from __future__ import annotations

import copy
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
RUNNER_DIR = ROOT_DIR / "yfd-runner"
MODELS_DIR = RUNNER_DIR / "models"

if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

import api as runner_api
import metrics as runner_metrics
import renderer as runner_renderer
import manuscript as runner_manuscript
import runner as runner_cli
import state as runner_state
import validator as runner_validator


class BridgeError(Exception):
    """Raised when the service layer cannot fulfill a request."""


class ValidationBridgeError(BridgeError):
    """Raised when structured validation errors should be returned to the client."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__("Validation failed")


class JobConflictBridgeError(BridgeError):
    """Raised when a run already has an active queued or running job."""

    def __init__(self, run_id: str, active_job_id: str):
        self.run_id = run_id
        self.active_job_id = active_job_id
        super().__init__(f"Run already has an active job: {active_job_id}")


class JobCancelledBridgeError(BridgeError):
    """Raised internally when a queued or running job is cooperatively cancelled."""


JOBS_LOCK = threading.Lock()
JOBS: dict[str, dict[str, Any]] = {}
ACTIVE_RUN_JOBS: dict[str, str] = {}
DEFAULT_REVIEW_POLICY = {
    "cascade": "auto",
    "plan": "manual",
    "draft": "manual",
    "repetition_audit": "auto",
    "style": "auto",
    "craft": "auto",
    "final": "manual",
    "summary": "auto",
}
REVIEW_POLICIES = {"auto", "manual", "on_warning"}
STEP_SETTINGS_ORDER = ["cascade", "plan", "draft", "repetition", "style", "craft", "final", "summary"]
DOSSIER_LABEL_DEFAULTS = {
    "brain_dump": ["section_1.required_data_layer"],
    "synopsis": ["section_2.story_concept"],
    "character_notes": ["section_3.protagonist_operating_systems"],
    "supporting_cast": ["section_4.supporting_cast"],
    "world_notes": ["section_5.story_world"],
    "style_notes": ["section_8.writing_style_rules"],
    "genre_notes": ["section_9.genre_lens"],
    "beat_sheet": ["chapter_outline_inputs"],
}
DOSSIER_TARGET_SECTIONS = {
    "section_2.story_concept": "section_2_story_concept",
    "section_3.protagonist_operating_systems": "section_3_protagonist_operating_systems",
    "section_4.supporting_cast": "section_4_supporting_cast",
    "section_5.story_world": "section_5_story_world",
    "section_8.writing_style_rules": "section_8_writing_style_rules",
    "section_9.genre_lens": "section_9_genre_lens",
    "chapter_outline_inputs": "section_12_chapter_outlines_setup",
}


def _validate_relative_name(name: str, suffix: str) -> str:
    candidate = Path(name)
    if candidate.name != name or candidate.suffix != suffix:
        raise BridgeError(f"Invalid file name: {name}")
    return name


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.rename(tmp_path, path)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _require_absolute_path(path_str: str, label: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        raise ValidationBridgeError(
            [
                {
                    "code": f"{label}_not_absolute",
                    "message": f"{label.replace('_', ' ').capitalize()} must be an absolute path.",
                }
            ]
        )
    return path


def _normalize_text_file(content: str) -> str:
    return content if content.endswith("\n") else content + "\n"


def _sorted_run_paths() -> list[Path]:
    return sorted(runner_state.STATE_DIR.glob("*.json"))


def _normalize_step_name(step: str) -> str:
    try:
        return runner_renderer.normalize_step_name(step)
    except Exception as exc:  # pragma: no cover - surfaced through API
        raise BridgeError(str(exc)) from exc


def _storage_step_name(step: str) -> str:
    normalized = _normalize_step_name(step)
    return "repetition_audit" if normalized == "repetition" else normalized


def _chapter_numbers(run_data: dict[str, Any]) -> list[int]:
    return sorted(int(key) for key in run_data.get("chapters", {}).keys())


def _latest_step(chapter_data: dict[str, Any]) -> str | None:
    for step_name in ("summary", "final", "craft", "style", "repetition_audit", "draft", "plan"):
        if chapter_data.get(step_name):
            return step_name
    return None


def _run_summary(path: Path) -> dict[str, Any]:
    run_id = path.stem
    data = runner_state.load_state(run_id)
    chapter_numbers = _chapter_numbers(data)
    current_chapter = chapter_numbers[-1] if chapter_numbers else None
    latest_step = None
    if current_chapter is not None:
        latest_step = _latest_step(data.get("chapters", {}).get(str(current_chapter), {}))
    metrics = data.get("metrics", {}) if isinstance(data.get("metrics", {}), dict) else {}
    total_tokens_in = int(metrics.get("total_tokens_in", 0) or 0)
    total_tokens_out = int(metrics.get("total_tokens_out", 0) or 0)

    return {
        "run_id": run_id,
        "path": _display_path(path),
        "project": data.get("project"),
        "total_chapters": data.get("total_chapters"),
        "current_chapter": current_chapter,
        "latest_completed_step": latest_step,
        "latest_step": latest_step,
        "updated_at": data.get("updated_at"),
        "created_at": data.get("created_at"),
        "total_tokens": total_tokens_in + total_tokens_out,
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
        "total_cost_usd": float(metrics.get("total_cost_usd", 0.0) or 0.0),
        "total_word_count": int(metrics.get("total_word_count", 0) or 0),
    }


def list_runs() -> list[dict[str, Any]]:
    return [_run_summary(path) for path in _sorted_run_paths()]


def _load_run_data(run_id: str) -> dict[str, Any]:
    try:
        return runner_state.load_state(run_id)
    except Exception as exc:  # pragma: no cover - passed through as API 404/400
        raise BridgeError(str(exc)) from exc


def get_run(run_id: str) -> dict[str, Any]:
    data = _load_run_data(run_id)
    return {
        "run_id": run_id,
        "state_path": _display_path(runner_state.state_path(run_id)),
        "data": data,
    }


def list_templates() -> list[dict[str, str]]:
    templates: list[dict[str, str]] = []
    for path in sorted(runner_renderer.TEMPLATES_DIR.glob("*.j2")):
        templates.append(
            {
                "name": path.name,
                "path": _display_path(path),
            }
        )
    return templates


def get_template(name: str) -> dict[str, str]:
    safe_name = _validate_relative_name(name, ".j2")
    path = runner_renderer.TEMPLATES_DIR / safe_name
    if not path.exists():
        raise BridgeError(f"Template not found: {name}")
    return {
        "name": path.name,
        "path": _display_path(path),
        "content": path.read_text(encoding="utf-8"),
    }


def update_template(name: str, content: str) -> dict[str, str]:
    safe_name = _validate_relative_name(name, ".j2")
    path = runner_renderer.TEMPLATES_DIR / safe_name
    if not path.exists():
        raise BridgeError(f"Template not found: {name}")

    if not content.strip():
        raise BridgeError("Template content must not be empty")

    # Validate syntax before write while preserving the exact source content.
    try:
        runner_renderer.build_environment().parse(content)
    except Exception as exc:  # pragma: no cover - surfaced through API
        raise BridgeError(f"Template validation failed: {exc}") from exc

    normalized = _normalize_text_file(content)
    _write_text_atomic(path, normalized)
    return get_template(safe_name)


def list_models() -> list[dict[str, str]]:
    models: list[dict[str, str]] = []
    for path in sorted(MODELS_DIR.glob("*.yaml")):
        models.append(
            {
                "name": path.name,
                "path": _display_path(path),
            }
        )
    return models


def get_model(name: str) -> dict[str, Any]:
    safe_name = _validate_relative_name(name, ".yaml")
    path = MODELS_DIR / safe_name
    if not path.exists():
        raise BridgeError(f"Model config not found: {name}")

    content = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - surfaced through API
        raise BridgeError(f"Model YAML is invalid: {exc}") from exc

    if not isinstance(data, dict):
        raise BridgeError(f"Model YAML must be a mapping: {name}")

    return {
        "name": path.name,
        "path": _display_path(path),
        "content": content,
        "data": data,
    }


def update_model(name: str, content: str) -> dict[str, Any]:
    safe_name = _validate_relative_name(name, ".yaml")
    path = MODELS_DIR / safe_name
    if not path.exists():
        raise BridgeError(f"Model config not found: {name}")

    if not content.strip():
        raise BridgeError("Model content must not be empty")

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:  # pragma: no cover - surfaced through API
        raise BridgeError(f"Model validation failed: {exc}") from exc

    if not isinstance(data, dict):
        raise BridgeError("Model YAML must parse to a mapping")
    if not data.get("model"):
        raise BridgeError("Model YAML must define a non-empty 'model' field")

    normalized = _normalize_text_file(content)
    _write_text_atomic(path, normalized)
    return get_model(safe_name)


def get_config() -> dict[str, Any]:
    path = runner_state.CONFIG_PATH
    content = path.read_text(encoding="utf-8")
    data = runner_state.load_config(path)
    return {
        "path": _display_path(path),
        "content": content,
        "data": data,
    }


def update_config(content: str) -> dict[str, Any]:
    if not content.strip():
        raise BridgeError("Config content must not be empty")

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:  # pragma: no cover - surfaced through API
        raise BridgeError(f"Config validation failed: {exc}") from exc

    if not isinstance(data, dict):
        raise BridgeError("Config YAML must parse to a mapping")

    normalized = _normalize_text_file(content)
    _write_text_atomic(runner_state.CONFIG_PATH, normalized)
    return get_config()


def _canonical_step_settings_name(step: str) -> str:
    normalized = step.strip().lower().replace("-", "_")
    aliases = {
        "repetition_audit": "repetition",
        "edit_style": "style",
        "edit_craft": "craft",
    }
    canonical = aliases.get(normalized, normalized)
    if canonical not in STEP_SETTINGS_ORDER:
        raise ValidationBridgeError(
            [{"code": "step_invalid", "message": f"Unsupported step: {step}"}]
        )
    return canonical


def _step_settings_payload(config: dict[str, Any], step: str) -> dict[str, Any]:
    canonical = _canonical_step_settings_name(step)
    project = config.get("project", {}) if isinstance(config.get("project", {}), dict) else {}
    default_model = project.get("default_model_config", "default")
    step_models = config.get("step_models", {}) if isinstance(config.get("step_models", {}), dict) else {}
    step_overrides = config.get("step_overrides", {}) if isinstance(config.get("step_overrides", {}), dict) else {}
    overrides = step_overrides.get(canonical, {})
    if not isinstance(overrides, dict):
        overrides = {}

    extras = {
        key: copy.deepcopy(value)
        for key, value in overrides.items()
        if key not in {"max_tokens", "temperature"}
    }
    return {
        "step": canonical,
        "model_config": step_models.get(canonical) or default_model,
        "max_tokens": overrides.get("max_tokens"),
        "temperature": overrides.get("temperature"),
        "extras": extras,
    }


def get_step_settings() -> dict[str, Any]:
    config = runner_state.load_config(runner_state.CONFIG_PATH)
    return {
        "steps": {
            step: _step_settings_payload(config, step)
            for step in STEP_SETTINGS_ORDER
        }
    }


def update_step_settings(
    step: str,
    *,
    model_config: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    canonical = _canonical_step_settings_name(step)
    if max_tokens is not None and max_tokens <= 0:
        raise ValidationBridgeError(
            [{"code": "max_tokens_invalid", "message": "max_tokens must be greater than 0."}]
        )
    if temperature is not None and temperature < 0:
        raise ValidationBridgeError(
            [{"code": "temperature_invalid", "message": "temperature must be >= 0."}]
        )
    if extras is not None and not isinstance(extras, dict):
        raise ValidationBridgeError(
            [{"code": "extras_invalid", "message": "extras must be an object if provided."}]
        )

    config = runner_state.load_config(runner_state.CONFIG_PATH)
    updated = copy.deepcopy(config)
    updated.setdefault("step_models", {})
    updated.setdefault("step_overrides", {})
    if not isinstance(updated["step_models"], dict) or not isinstance(updated["step_overrides"], dict):
        raise BridgeError("Config step settings sections are invalid")

    if model_config is not None:
        normalized_model = model_config.strip()
        if not normalized_model:
            raise ValidationBridgeError(
                [{"code": "model_config_invalid", "message": "model_config must not be empty."}]
            )
        updated["step_models"][canonical] = normalized_model

    existing_overrides = updated["step_overrides"].get(canonical, {})
    if not isinstance(existing_overrides, dict):
        existing_overrides = {}
    next_overrides = copy.deepcopy(existing_overrides)

    if max_tokens is not None:
        next_overrides["max_tokens"] = int(max_tokens)
    if temperature is not None:
        next_overrides["temperature"] = float(temperature)
    if extras is not None:
        for key in list(next_overrides.keys()):
            if key not in {"max_tokens", "temperature"}:
                del next_overrides[key]
        for key, value in extras.items():
            if key in {"max_tokens", "temperature"}:
                continue
            next_overrides[key] = value

    updated["step_overrides"][canonical] = next_overrides
    normalized = _normalize_text_file(yaml.safe_dump(updated, sort_keys=False))
    _write_text_atomic(runner_state.CONFIG_PATH, normalized)
    latest = runner_state.load_config(runner_state.CONFIG_PATH)
    return _step_settings_payload(latest, canonical)


def _ensure_studio(data: dict[str, Any]) -> dict[str, Any]:
    studio = data.setdefault("studio", {})
    if not isinstance(studio, dict):
        raise BridgeError("Run studio state is invalid")
    return studio


def _ensure_review_state(data: dict[str, Any], chapter: int, step: str) -> dict[str, Any]:
    studio = _ensure_studio(data)
    review_state = studio.setdefault("review_state", {})
    if not isinstance(review_state, dict):
        raise BridgeError("Run studio.review_state is invalid")

    chapter_key = str(chapter)
    chapter_review = review_state.setdefault(chapter_key, {})
    if not isinstance(chapter_review, dict):
        raise BridgeError(f"Run review_state chapter bucket is invalid: {chapter_key}")

    step_review = chapter_review.setdefault(step, {})
    if not isinstance(step_review, dict):
        raise BridgeError(f"Run review_state step bucket is invalid: chapter={chapter_key} step={step}")

    return step_review


def _ensure_candidate_outputs(data: dict[str, Any]) -> list[dict[str, Any]]:
    studio = _ensure_studio(data)
    candidate_outputs = studio.setdefault("candidate_outputs", [])
    if not isinstance(candidate_outputs, list):
        raise BridgeError("Run studio.candidate_outputs is invalid")
    return candidate_outputs


def _new_candidate_id() -> str:
    return f"cand_{uuid4().hex[:12]}"


def _new_job_id() -> str:
    return f"job_{uuid4().hex[:12]}"


def _job_snapshot(job_id: str) -> dict[str, Any]:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            raise BridgeError(f"Job not found: {job_id}")
        return copy.deepcopy(job)


def _job_event(event: str, message: str, **fields: Any) -> dict[str, Any]:
    payload = {
        "event": event,
        "message": message,
        "timestamp": runner_state.now_iso(),
    }
    payload.update(fields)
    return payload


def _append_job_event(job_id: str, event: str, message: str, **fields: Any) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return
        job.setdefault("events", []).append(_job_event(event, message, **fields))


def _cancel_requested(job_id: str) -> bool:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return False
        return bool(job.get("cancel_requested"))


def _raise_if_cancel_requested(job_id: str, message: str = "Job cancelled before starting the next unit of work") -> None:
    if _cancel_requested(job_id):
        raise JobCancelledBridgeError(message)


def _finish_job(job_id: str, *, status: str, result: dict[str, Any] | None = None, error: str | None = None) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return
        job["status"] = status
        job["finished_at"] = runner_state.now_iso()
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        run_id = str(job.get("run_id", ""))
        if run_id and ACTIVE_RUN_JOBS.get(run_id) == job_id:
            del ACTIVE_RUN_JOBS[run_id]


def _run_job(job_id: str, worker) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return
        job["status"] = "running"
        job["started_at"] = runner_state.now_iso()

    _append_job_event(job_id, "job_started", "Job started")
    try:
        _raise_if_cancel_requested(job_id, "Job cancelled before execution started")
        result = worker(job_id)
    except JobCancelledBridgeError as exc:
        _append_job_event(job_id, "job_cancelled", str(exc))
        _finish_job(job_id, status="cancelled", error=str(exc))
        return
    except Exception as exc:  # pragma: no cover - exercised via API tests instead
        if _is_validation_failure_message(str(exc)):
            _append_job_event(job_id, "validation_failed", str(exc))
        _append_job_event(job_id, "job_failed", str(exc))
        _finish_job(job_id, status="failed", error=str(exc))
        return

    _append_job_event(job_id, "job_finished", "Job finished successfully")
    _finish_job(job_id, status="succeeded", result=result)


def _queue_job(
    *,
    run_id: str,
    job_type: str,
    target: dict[str, Any],
    worker,
) -> dict[str, Any]:
    _load_run_data(run_id)
    with JOBS_LOCK:
        active_job_id = ACTIVE_RUN_JOBS.get(run_id)
        if active_job_id:
            active_job = JOBS.get(active_job_id)
            if active_job and active_job.get("status") in {"queued", "running"}:
                raise JobConflictBridgeError(run_id, active_job_id)

        job_id = _new_job_id()
        record = {
            "job_id": job_id,
            "job_type": job_type,
            "status": "queued",
            "run_id": run_id,
            "target": target,
            "created_at": runner_state.now_iso(),
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
            "cancel_requested": False,
            "cancel_requested_at": None,
            "events": [_job_event("job_queued", "Job queued", **target)],
        }
        JOBS[job_id] = record
        ACTIVE_RUN_JOBS[run_id] = job_id
        queued_snapshot = copy.deepcopy(record)

    thread = threading.Thread(target=_run_job, args=(job_id, worker), daemon=True)
    thread.start()
    return queued_snapshot


def get_job(job_id: str) -> dict[str, Any]:
    return _job_snapshot(job_id)


def iter_job_events(job_id: str, poll_interval: float = 0.05):
    sent = 0
    while True:
        snapshot = _job_snapshot(job_id)
        events = snapshot.get("events", [])
        while sent < len(events):
            payload = events[sent]
            body = json.dumps(payload, ensure_ascii=True)
            yield f"event: {payload.get('event', 'message')}\ndata: {body}\n\n"
            sent += 1

        if snapshot.get("status") in {"succeeded", "failed", "cancelled"}:
            return
        time.sleep(poll_interval)


def cancel_job(job_id: str) -> dict[str, Any]:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            raise BridgeError(f"Job not found: {job_id}")

        status = str(job.get("status"))
        if status in {"succeeded", "failed", "cancelled"}:
            return copy.deepcopy(job)

        if not job.get("cancel_requested"):
            job["cancel_requested"] = True
            job["cancel_requested_at"] = runner_state.now_iso()
            job.setdefault("events", []).append(
                _job_event(
                    "cancel_requested",
                    "Cancellation requested",
                    job_id=job_id,
                    run_id=job.get("run_id"),
                )
            )

        if status == "queued":
            job["status"] = "cancelled"
            job["finished_at"] = runner_state.now_iso()
            job["error"] = "Job cancelled before execution started"
            job.setdefault("events", []).append(
                _job_event(
                    "job_cancelled",
                    "Job cancelled before execution started",
                    job_id=job_id,
                    run_id=job.get("run_id"),
                )
            )
            run_id = str(job.get("run_id", ""))
            if run_id and ACTIVE_RUN_JOBS.get(run_id) == job_id:
                del ACTIVE_RUN_JOBS[run_id]

        return copy.deepcopy(job)


def _validate_step_slot_exists(data: dict[str, Any], chapter: int, step: str) -> None:
    if step == "plan":
        return

    chapter_bucket = data.get("chapters", {}).get(str(chapter))
    if chapter_bucket is None:
        raise ValidationBridgeError(
            [
                {
                    "code": "chapter_not_found",
                    "message": f"Chapter does not exist for this run: {chapter}",
                }
            ]
        )


def _run_output_dir_from_data(data: dict[str, Any]) -> Path | None:
    studio = data.get("studio", {})
    if not isinstance(studio, dict):
        return None

    run_settings = studio.get("run_settings", {})
    if not isinstance(run_settings, dict):
        return None

    output_dir = run_settings.get("output_dir")
    if not output_dir:
        return None
    return Path(str(output_dir))


def _build_manuscript_for_run(run_id: str) -> Path:
    data = _load_run_data(run_id)
    return runner_manuscript.build_manuscript(run_id, output_dir=_run_output_dir_from_data(data))


def _response_text(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content)


def _is_validation_failure_message(message: str) -> bool:
    lowered = message.lower()
    return "validation failed" in lowered or "invalid prose output" in lowered or "cascade validation failed" in lowered


def _steering_prompt(prompt: str, steering_note: str) -> str:
    note = steering_note.strip()
    if not note:
        return prompt
    return f"## Steering Note\n{note}\n\n---\n\n{prompt}"


def _review_policy_for_step(data: dict[str, Any], step: str) -> str:
    studio = data.get("studio", {})
    if not isinstance(studio, dict):
        return "manual"
    run_settings = studio.get("run_settings", {})
    if not isinstance(run_settings, dict):
        return "manual"
    review_policy = run_settings.get("review_policy", {})
    if not isinstance(review_policy, dict):
        return DEFAULT_REVIEW_POLICY.get(step, "manual")
    policy = str(review_policy.get(step) or DEFAULT_REVIEW_POLICY.get(step, "manual")).strip().lower()
    if policy not in REVIEW_POLICIES:
        return DEFAULT_REVIEW_POLICY.get(step, "manual")
    return policy


def _review_checkpoint_for_policy(policy: str, *, warnings_present: bool) -> tuple[bool, str, str]:
    normalized = policy.strip().lower() or "manual"
    if normalized not in REVIEW_POLICIES:
        normalized = "manual"

    if normalized == "manual":
        return True, "policy", "pending"
    if normalized == "on_warning" and warnings_present:
        return True, "warning", "pending"
    return False, "manual", "not_required"


def _step_event_fields(
    *,
    chapter: int | None = None,
    step: str | None = None,
    section_number: int | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if chapter is not None:
        fields["chapter"] = chapter
    if step is not None:
        fields["step"] = step
    if section_number is not None:
        fields["section_number"] = section_number
    return fields


def _append_step_failure_event(
    job_id: str,
    message: str,
    *,
    chapter: int | None = None,
    step: str | None = None,
    section_number: int | None = None,
) -> None:
    fields = _step_event_fields(chapter=chapter, step=step, section_number=section_number)
    if _is_validation_failure_message(message):
        _append_job_event(job_id, "validation_failed", message, **fields)
    _append_job_event(job_id, "step_failed", message, **fields)


def _call_model_step_with_job_events(
    *,
    prompt: str,
    step_name: str,
    run_id: str,
    chapter: int | None,
    job_id: str,
    model_config: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    canonical_step = runner_api.normalize_step_name(step_name)
    event_fields = _step_event_fields(chapter=chapter, step=canonical_step)
    warnings: list[dict[str, Any]] = []

    def attempt_logger(payload: dict[str, Any]) -> None:
        attempt = int(payload.get("attempt") or 0)
        status = str(payload.get("status") or "")
        message = f"Attempt {attempt} {status}: {canonical_step}" if attempt else f"Attempt event: {canonical_step}"
        fields = {
            **event_fields,
            "attempt": attempt,
            "model_config": payload.get("model"),
            "estimated_prompt_tokens": payload.get("estimated_prompt_tokens"),
        }
        if status == "started":
            _append_job_event(job_id, "attempt_started", f"Attempt {attempt} started: {canonical_step}", **fields)
        elif status == "success":
            _append_job_event(job_id, "attempt_succeeded", f"Attempt {attempt} succeeded: {canonical_step}", **fields)
        elif status == "error":
            _append_job_event(
                job_id,
                "attempt_failed",
                f"Attempt {attempt} failed: {canonical_step}",
                error=payload.get("error"),
                **fields,
            )
        else:
            _append_job_event(job_id, "attempt_event", message, **fields)

    result = runner_api.call_step(
        prompt,
        canonical_step,
        run_id=run_id,
        chapter=chapter,
        cli_model_config=model_config,
        attempt_logger=attempt_logger,
    )

    if canonical_step != "cascade":
        config = runner_state.load_config()
        steps_config = config.get("steps", {}) if isinstance(config.get("steps", {}), dict) else {}
        warn_context_tokens = int(steps_config.get("warn_context_tokens", 0))
        estimated_prompt_tokens = int(result.get("estimated_prompt_tokens") or 0)
        if warn_context_tokens and estimated_prompt_tokens > warn_context_tokens:
            warning = {
                "code": "prompt_tokens_high",
                "message": (
                    f"Estimated prompt tokens for step '{canonical_step}' are {estimated_prompt_tokens}, "
                    f"which exceeds warn_context_tokens={warn_context_tokens}."
                ),
            }
            warnings.append(warning)
            _append_job_event(
                job_id,
                "warning",
                warning["message"],
                warn_context_tokens=warn_context_tokens,
                estimated_prompt_tokens=estimated_prompt_tokens,
                **event_fields,
            )

    attempts = int(result.get("attempts") or 1)
    if attempts > 1:
        warning = {
            "code": "retry_recovered",
            "message": f"Step '{canonical_step}' succeeded after {attempts} attempts.",
        }
        warnings.append(warning)
        _append_job_event(job_id, "warning", warning["message"], attempt_count=attempts, **event_fields)

    return result, warnings


def _save_step_output_and_metrics(
    run_id: str,
    chapter: int,
    step: str,
    *,
    content: str,
    result: dict[str, Any],
) -> None:
    runner_state.save_step_output(run_id, chapter, step, content)
    response = result["response"]
    runner_metrics.record_call(
        run_id,
        chapter,
        step,
        result["model_config"]["model"],
        response,
        content=content,
        extra_fields={"attempts": result["attempts"]},
    )
    runner_metrics.update_cumulative(_load_run_data(run_id).get("project", "project"), run_id)


def _set_review_state(
    run_id: str,
    chapter: int,
    step: str,
    *,
    review_required: bool,
    review_reason: str,
    review_status: str,
    approved_candidate_id: str | None = None,
) -> None:
    reviewed_at = runner_state.now_iso() if review_status != "pending" else None

    def mutator(data: dict[str, Any]) -> None:
        step_review = _ensure_review_state(data, chapter, step)
        step_review.update(
            {
                "review_required": review_required,
                "review_reason": review_reason,
                "review_status": review_status,
                "approved_candidate_id": approved_candidate_id,
                "last_reviewed_at": reviewed_at,
            }
        )

    runner_state.update_state(run_id, mutator)


def _record_initial_review_checkpoint(
    run_id: str,
    chapter: int,
    step: str,
    content: str,
    *,
    review_required: bool,
    review_reason: str,
    review_status: str,
) -> str | None:
    candidate_id: str | None = None
    if review_required:
        candidate = _candidate_record(
            chapter=chapter,
            step=step,
            source="initial_run",
            content=content.strip(),
        )
        candidate_id = candidate["candidate_id"]

        def add_candidate(data: dict[str, Any]) -> None:
            _ensure_candidate_outputs(data).append(candidate)

        runner_state.update_state(run_id, add_candidate)

    _set_review_state(
        run_id,
        chapter,
        step,
        review_required=review_required,
        review_reason=review_reason,
        review_status=review_status,
        approved_candidate_id=None,
    )
    return candidate_id


def _sync_summary_and_manuscript_if_needed(run_id: str, step: str) -> dict[str, Any] | None:
    if step != "summary":
        return None

    updated = runner_state.rebuild_chapter_summaries(run_id)
    output_dir = _run_output_dir_from_data(updated)
    runner_manuscript.build_manuscript(run_id, output_dir=output_dir)
    return updated


def validate_worksheet_path(worksheet_path: str) -> dict[str, Any]:
    path = _require_absolute_path(worksheet_path, "worksheet_path")

    if not path.exists() or not path.is_file():
        return {
            "ok": False,
            "errors": [
                {
                    "code": "worksheet_not_found",
                    "message": f"Worksheet file does not exist: {path}",
                }
            ],
        }

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "errors": [
                {
                    "code": "worksheet_unreadable",
                    "message": f"Worksheet file could not be read: {exc}",
                }
            ],
        }

    return validate_worksheet_text(content)


def render_cascade_preview(run_id: str, section_number: int) -> dict[str, Any]:
    try:
        rendered = runner_renderer.render_cascade(run_id, section_number)
    except Exception as exc:  # pragma: no cover - passed through as API 400
        raise BridgeError(str(exc)) from exc

    return {
        "run_id": run_id,
        "section_number": section_number,
        "template_name": runner_renderer.template_name_for_step("cascade"),
        "rendered": rendered,
    }


def create_run(
    run_id: str,
    worksheet_path: str,
    model_config: str | None = None,
    output_dir: str | None = None,
    review_policy: dict[str, str] | None = None,
) -> dict[str, Any]:
    run_id = run_id.strip()
    if not run_id:
        raise ValidationBridgeError(
            [{"code": "run_id_required", "message": "run_id is required."}]
        )

    validation = validate_worksheet_path(worksheet_path)
    if not validation["ok"]:
        raise ValidationBridgeError(validation["errors"])

    state_file = runner_state.state_path(run_id)
    if state_file.exists():
        raise ValidationBridgeError(
            [{"code": "run_id_exists", "message": f"Run already exists: {run_id}"}]
        )

    output_path_value: str | None = None
    if output_dir is not None:
        output_path_value = str(_require_absolute_path(output_dir, "output_dir"))

    try:
        runner_state.initialize_run(run_id, worksheet_path, model_config=model_config)
        runner_state.update_state(
            run_id,
            lambda data: data.update(
                {
                    "studio": {
                        "run_settings": {
                            "output_dir": output_path_value,
                            "review_policy": review_policy or {},
                            "default_steering_note": "",
                            "created_from": "worksheet",
                        }
                    }
                }
            ),
        )
    except ValidationBridgeError:
        raise
    except Exception as exc:  # pragma: no cover - surfaced through API
        raise BridgeError(str(exc)) from exc

    return {
        "run_id": run_id,
        "status": "created",
        "worksheet_validation": validation,
        "state_path": _display_path(runner_state.state_path(run_id)),
    }


def _normalize_dossier_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized


def _slug_label(label: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    return normalized or "block"


def _dossier_blocks(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dossier_blocks: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        label = _slug_label(str(record.get("label", "")))
        normalized_text = _normalize_dossier_text(str(record.get("text", "")))
        if not normalized_text:
            continue
        dossier_blocks.append(
            {
                "block_id": f"blk_{index:03d}",
                "label": label,
                "source_type": str(record.get("source_type", "")).strip() or "pasted_text",
                "source_name": str(record.get("source_name", "")).strip() or f"block-{index}",
                "raw_text": str(record.get("text", "")),
                "normalized_text": normalized_text,
                "included": True,
                "mapping_targets": DOSSIER_LABEL_DEFAULTS.get(label, []),
                "created_at": runner_state.now_iso(),
            }
        )
    return dossier_blocks


def _required_data_layer_from_blocks(dossier_blocks: list[dict[str, Any]]) -> str:
    mapped = [block for block in dossier_blocks if "section_1.required_data_layer" in block.get("mapping_targets", [])]
    source_blocks = mapped or dossier_blocks
    lines: list[str] = []
    for block in source_blocks:
        lines.append(f"**{block['label']}:** {block['normalized_text']}")
    return "\n\n".join(lines).strip()


def _worksheet_draft_from_blocks(dossier_blocks: list[dict[str, Any]]) -> str:
    sections: list[str] = []
    required_data_layer = _required_data_layer_from_blocks(dossier_blocks)
    sections.append(
        "## section_1_required_data_layer\n\n"
        "### required_data_layer\n\n"
        f"{required_data_layer}"
    )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for block in dossier_blocks:
        for target in block.get("mapping_targets", []):
            if target == "section_1.required_data_layer":
                continue
            grouped.setdefault(target, []).append(block)

    for target, section_key in DOSSIER_TARGET_SECTIONS.items():
        blocks = grouped.get(target, [])
        if not blocks:
            continue
        body_lines = [
            f"### imported_{_slug_label(block['label'])}\n\n{block['normalized_text']}"
            for block in blocks
        ]
        sections.append(f"## {section_key}\n\n" + "\n\n".join(body_lines).strip())

    return "\n\n---\n\n".join(section.rstrip() for section in sections).rstrip() + "\n"


def create_project_from_dossier(
    run_id: str,
    blocks: list[dict[str, Any]],
    model_config: str | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    target_run_id = run_id.strip()
    if not target_run_id:
        raise ValidationBridgeError(
            [{"code": "run_id_required", "message": "run_id is required."}]
        )
    if runner_state.state_path(target_run_id).exists():
        raise ValidationBridgeError(
            [{"code": "run_id_exists", "message": f"Run already exists: {target_run_id}"}]
        )

    dossier_blocks = _dossier_blocks(blocks)
    if not dossier_blocks:
        raise ValidationBridgeError(
            [{"code": "empty_dossier", "message": "At least one non-empty dossier block is required."}]
        )

    output_path_value: str | None = None
    if output_dir is not None:
        output_path_value = str(_require_absolute_path(output_dir, "output_dir"))

    worksheet_draft = _worksheet_draft_from_blocks(dossier_blocks)
    validation = validate_worksheet_text(worksheet_draft)
    if not validation["ok"]:
        raise ValidationBridgeError(validation["errors"])

    config = runner_state.load_config(runner_state.CONFIG_PATH)
    project = config.get("project", {}) if isinstance(config.get("project", {}), dict) else {}
    created_at = runner_state.now_iso()
    state_payload = {
        "run_id": target_run_id,
        "project": project.get("name", "project"),
        "model_config": model_config,
        "worksheet": worksheet_draft,
        "instructions": runner_state.extract_required_data_layer(worksheet_draft),
        "total_chapters": project.get("total_chapters", 0),
        "chapter_summaries": "",
        "metrics": runner_state.default_metrics(),
        "chapters": {},
        "created_at": created_at,
        "updated_at": created_at,
        "studio": {
            "run_settings": {
                "output_dir": output_path_value,
                "review_policy": {},
                "default_steering_note": "",
                "created_from": "dossier",
            },
            "dossier_blocks": dossier_blocks,
        },
    }

    try:
        runner_state.save_state(target_run_id, state_payload)
    except Exception as exc:  # pragma: no cover - surfaced through API
        raise BridgeError(str(exc)) from exc

    return {
        "run_id": target_run_id,
        "status": "draft_ready",
        "dossier_blocks": [
            {
                "block_id": block["block_id"],
                "label": block["label"],
                "mapping_targets": block["mapping_targets"],
            }
            for block in dossier_blocks
        ],
        "worksheet_draft": worksheet_draft,
        "state_path": _display_path(runner_state.state_path(target_run_id)),
    }


def branch_run(
    run_id: str,
    new_run_id: str,
    branched_from_chapter: int | None = None,
    branch_note: str = "",
) -> dict[str, Any]:
    source_data = _load_run_data(run_id)
    target_run_id = new_run_id.strip()
    if not target_run_id:
        raise ValidationBridgeError(
            [{"code": "new_run_id_required", "message": "new_run_id is required."}]
        )
    if target_run_id == run_id:
        raise ValidationBridgeError(
            [{"code": "new_run_id_invalid", "message": "new_run_id must differ from the source run id."}]
        )
    if runner_state.state_path(target_run_id).exists():
        raise ValidationBridgeError(
            [{"code": "run_id_exists", "message": f"Run already exists: {target_run_id}"}]
        )
    if branched_from_chapter is not None and branched_from_chapter < 1:
        raise ValidationBridgeError(
            [{"code": "branched_from_chapter_invalid", "message": "branched_from_chapter must be >= 1."}]
        )

    branched = copy.deepcopy(source_data)
    branched["run_id"] = target_run_id
    branched["created_at"] = runner_state.now_iso()
    branched["updated_at"] = branched["created_at"]

    studio = branched.setdefault("studio", {})
    if not isinstance(studio, dict):
        raise BridgeError("Run studio state is invalid")
    studio["branch"] = {
        "parent_run_id": run_id,
        "branched_from_chapter": branched_from_chapter,
        "branch_note": branch_note.strip(),
        "branched_at": runner_state.now_iso(),
    }

    try:
        runner_state.save_state(target_run_id, branched)
    except Exception as exc:  # pragma: no cover - surfaced through API
        raise BridgeError(str(exc)) from exc

    return {
        "run_id": target_run_id,
        "parent_run_id": run_id,
        "status": "created",
        "state_path": _display_path(runner_state.state_path(target_run_id)),
    }


def _execute_step_once(
    run_id: str,
    chapter: int,
    step: str,
    *,
    model_config: str | None,
    force: bool,
    job_id: str,
) -> dict[str, Any]:
    storage_step = _storage_step_name(step)
    manuscript_path: str | None = None
    _raise_if_cancel_requested(job_id)
    _append_job_event(job_id, "step_started", f"Step started: {storage_step}", chapter=chapter, step=storage_step)
    try:
        runner_cli.maybe_prompt_overwrite(run_id, chapter, storage_step, force=force)
        prompt = runner_renderer.render_step(run_id, chapter, storage_step)
        _append_job_event(
            job_id,
            "prompt_rendered",
            f"Prompt rendered: {storage_step}",
            chapter=chapter,
            step=storage_step,
            prompt_chars=len(prompt),
        )
        result, warnings = _call_model_step_with_job_events(
            prompt=prompt,
            step_name=storage_step,
            run_id=run_id,
            chapter=chapter,
            job_id=job_id,
            model_config=model_config,
        )
        response = result["response"]
        content = _response_text(response).strip()
        if not content:
            raise BridgeError("Model returned an empty response body")

        if storage_step in {"draft", "final"}:
            min_word_count = 500
            if storage_step == "final":
                draft_text = runner_state.get_step_output(run_id, chapter, "draft") or ""
                draft_word_count = runner_validator.count_words(draft_text)
                if draft_word_count:
                    min_word_count = max(min_word_count, int(draft_word_count * 0.4))

            ok, reason = runner_validator.check_prose_response(content, min_word_count=min_word_count)
            if not ok:
                fail_dir = runner_renderer.RENDERED_DIR / run_id
                fail_dir.mkdir(parents=True, exist_ok=True)
                fail_path = fail_dir / f"ch{chapter:02d}_{storage_step}_validation_fail.md"
                fail_path.write_text(content, encoding="utf-8")
                raise BridgeError(
                    f"Step '{storage_step}' produced invalid prose output ({reason}). Saved: {fail_path}"
                )

        _save_step_output_and_metrics(run_id, chapter, storage_step, content=content, result=result)
        if storage_step == "summary":
            _sync_summary_and_manuscript_if_needed(run_id, storage_step)
            output_dir = _run_output_dir_from_data(_load_run_data(run_id))
            manuscript_root = output_dir or runner_manuscript.OUTPUT_DIR
            manuscript_path = _display_path(manuscript_root / f"{run_id}_manuscript.md")
        _append_job_event(job_id, "step_succeeded", f"Step succeeded: {storage_step}", chapter=chapter, step=storage_step)
    except Exception as exc:
        _append_step_failure_event(job_id, str(exc), chapter=chapter, step=storage_step)
        raise

    data = _load_run_data(run_id)
    policy = _review_policy_for_step(data, storage_step)
    review_required, review_reason, review_status = _review_checkpoint_for_policy(
        policy,
        warnings_present=bool(warnings),
    )
    candidate_id = _record_initial_review_checkpoint(
        run_id,
        chapter,
        storage_step,
        content,
        review_required=review_required,
        review_reason=review_reason,
        review_status=review_status,
    )
    if review_required:
        message = "Review required due to warning" if review_reason == "warning" else f"Manual review required: {storage_step}"
        _append_job_event(
            job_id,
            "warning",
            message,
            chapter=chapter,
            step=storage_step,
            candidate_id=candidate_id,
            review_policy=policy,
            warning_count=len(warnings),
        )

    return {
        "step": storage_step,
        "review_policy": policy,
        "review_required": review_required,
        "candidate_id": candidate_id,
        "warning_count": len(warnings),
        "manuscript_path": manuscript_path,
    }


def _run_cascade_section_once(
    run_id: str,
    section_number: int,
    *,
    model_config: str | None,
    force: bool,
    job_id: str,
) -> dict[str, Any]:
    _raise_if_cancel_requested(job_id)
    sections = runner_state.parse_sections(runner_state.get_worksheet(run_id))
    target = next((item for item in sections if item["section_number"] == section_number), None)
    if target is None:
        raise ValidationBridgeError(
            [{"code": "section_not_found", "message": f"Unknown worksheet section: {section_number}"}]
        )

    _append_job_event(
        job_id,
        "step_started",
        f"Cascade section started: {target['section_key']}",
        section_number=section_number,
        step="cascade",
    )
    try:
        prompt = runner_renderer.render_cascade(run_id, section_number)
        _append_job_event(
            job_id,
            "prompt_rendered",
            f"Cascade prompt rendered: {target['section_key']}",
            section_number=section_number,
            step="cascade",
            prompt_chars=len(prompt),
        )
        result, _warnings = _call_model_step_with_job_events(
            prompt=prompt,
            step_name="cascade",
            run_id=run_id,
            chapter=None,
            job_id=job_id,
            model_config=model_config,
        )
        response = result["response"]
        content = _response_text(response).strip()
        if not content:
            raise BridgeError("Cascade returned an empty response body")

        if not force:
            config = runner_state.load_config()
            cascade_config = config.get("cascade", {})
            ok, reason = runner_validator.check_cascade_response(
                content,
                target["section_key"],
                bracket_pattern=cascade_config.get("bracket_pattern", runner_validator.DEFAULT_BRACKET_PATTERN),
                min_response_length=int(cascade_config.get("min_response_length", 50)),
            )
            if not ok:
                fail_dir = runner_renderer.RENDERED_DIR / run_id
                fail_dir.mkdir(parents=True, exist_ok=True)
                fail_path = fail_dir / f"cascade_fail_section_{section_number:02d}_{target['section_key']}.md"
                fail_path.write_text(content, encoding="utf-8")
                raise BridgeError(
                    f"Cascade validation failed for {target['section_key']}: {reason}. Saved: {fail_path}"
                )

        runner_state.save_worksheet_section(run_id, target["section_key"], content)
        runner_metrics.record_call(
            run_id,
            None,
            "cascade",
            result["model_config"]["model"],
            response,
            content=content,
            extra_fields={"attempts": result["attempts"], "section": target["section_key"]},
        )
        runner_metrics.update_cumulative(_load_run_data(run_id).get("project", "project"), run_id)
        _append_job_event(
            job_id,
            "step_succeeded",
            f"Cascade section completed: {target['section_key']}",
            section_number=section_number,
            step="cascade",
        )
    except Exception as exc:
        _append_step_failure_event(job_id, str(exc), section_number=section_number, step="cascade")
        raise

    return {
        "section_number": section_number,
        "section_key": target["section_key"],
    }


def queue_build_manuscript(run_id: str) -> dict[str, Any]:
    def worker(job_id: str) -> dict[str, Any]:
        _raise_if_cancel_requested(job_id)
        _append_job_event(job_id, "step_started", "Build manuscript started")
        output_path = _build_manuscript_for_run(run_id)
        _append_job_event(
            job_id,
            "step_succeeded",
            "Build manuscript finished",
            output_path=_display_path(output_path),
        )
        return {
            "run_id": run_id,
            "output_path": _display_path(output_path),
        }

    return _queue_job(
        run_id=run_id,
        job_type="build_manuscript",
        target={"run_id": run_id},
        worker=worker,
    )


def queue_execute_step(
    run_id: str,
    chapter: int,
    step: str,
    *,
    model_config: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    data = _load_run_data(run_id)
    storage_step = _storage_step_name(step)
    _validate_step_slot_exists(data, chapter, storage_step)

    def worker(job_id: str) -> dict[str, Any]:
        step_result = _execute_step_once(
            run_id,
            chapter,
            storage_step,
            model_config=model_config,
            force=force,
            job_id=job_id,
        )
        return {
            "run_id": run_id,
            "chapter": chapter,
            "step": storage_step,
            "review_policy": step_result["review_policy"],
            "review_required": step_result["review_required"],
            "candidate_id": step_result["candidate_id"],
            "manuscript_path": step_result["manuscript_path"],
        }

    return _queue_job(
        run_id=run_id,
        job_type="single_step",
        target={"run_id": run_id, "chapter": chapter, "step": storage_step},
        worker=worker,
    )


def queue_chapter_auto_run(
    run_id: str,
    chapter: int,
    *,
    model_config: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    def worker(job_id: str) -> dict[str, Any]:
        completed_steps: list[str] = []
        paused_at: dict[str, Any] | None = None
        manuscript_path: str | None = None
        for step_name in runner_cli.step_order_for_chapter(chapter):
            _raise_if_cancel_requested(job_id)
            step_result = _execute_step_once(
                run_id,
                chapter,
                step_name,
                model_config=model_config,
                force=force,
                job_id=job_id,
            )
            completed_steps.append(step_result["step"])
            if step_result["manuscript_path"]:
                manuscript_path = step_result["manuscript_path"]
            if step_result["review_required"]:
                paused_at = {
                    "step": step_result["step"],
                    "review_policy": step_result["review_policy"],
                    "candidate_id": step_result["candidate_id"],
                }
                break

        return {
            "run_id": run_id,
            "chapter": chapter,
            "completed_steps": completed_steps,
            "paused_at": paused_at,
            "manuscript_path": manuscript_path,
        }

    return _queue_job(
        run_id=run_id,
        job_type="chapter_auto_run",
        target={"run_id": run_id, "chapter": chapter},
        worker=worker,
    )


def queue_cascade_section(
    run_id: str,
    section_number: int,
    *,
    model_config: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    def worker(job_id: str) -> dict[str, Any]:
        result = _run_cascade_section_once(
            run_id,
            section_number,
            model_config=model_config,
            force=force,
            job_id=job_id,
        )
        return {"run_id": run_id, **result}

    return _queue_job(
        run_id=run_id,
        job_type="cascade_section",
        target={"run_id": run_id, "section_number": section_number, "step": "cascade"},
        worker=worker,
    )


def queue_cascade_auto(
    run_id: str,
    *,
    model_config: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    def worker(job_id: str) -> dict[str, Any]:
        completed_sections: list[dict[str, Any]] = []
        while True:
            _raise_if_cancel_requested(job_id)
            next_section = runner_state.get_next_incomplete_section(run_id)
            if next_section is None:
                break
            section_number = int(next_section[0])
            completed_sections.append(
                _run_cascade_section_once(
                    run_id,
                    section_number,
                    model_config=model_config,
                    force=force,
                    job_id=job_id,
                )
            )
        return {
            "run_id": run_id,
            "completed_sections": completed_sections,
        }

    return _queue_job(
        run_id=run_id,
        job_type="cascade_auto",
        target={"run_id": run_id, "step": "cascade"},
        worker=worker,
    )


def queue_rerun_step(
    run_id: str,
    chapter: int,
    step: str,
    *,
    steering_note: str = "",
    force: bool = False,
    review_mode: str = "manual",
    model_config: str | None = None,
) -> dict[str, Any]:
    del force
    review_mode = review_mode.strip().lower() or "manual"
    if review_mode not in REVIEW_POLICIES:
        raise ValidationBridgeError(
            [{"code": "review_mode_invalid", "message": f"Unsupported review_mode: {review_mode}"}]
        )

    data = _load_run_data(run_id)
    storage_step = _storage_step_name(step)
    _validate_step_slot_exists(data, chapter, storage_step)

    def worker(job_id: str) -> dict[str, Any]:
        _raise_if_cancel_requested(job_id)
        _append_job_event(
            job_id,
            "step_started",
            f"Rerun started: {storage_step}",
            chapter=chapter,
            step=storage_step,
        )
        try:
            prompt = runner_renderer.render_step(run_id, chapter, storage_step)
            prompt = _steering_prompt(prompt, steering_note)
            _append_job_event(
                job_id,
                "prompt_rendered",
                f"Prompt rendered: {storage_step}",
                chapter=chapter,
                step=storage_step,
                prompt_chars=len(prompt),
                steering_note=steering_note.strip(),
            )

            result, warnings = _call_model_step_with_job_events(
                prompt=prompt,
                step_name=storage_step,
                run_id=run_id,
                chapter=chapter,
                job_id=job_id,
                model_config=model_config,
            )
            response = result["response"]
            content = _response_text(response).strip()
            if not content:
                raise BridgeError("Model returned an empty response body")

            if storage_step in {"draft", "final"}:
                min_word_count = 500
                if storage_step == "final":
                    draft_text = runner_state.get_step_output(run_id, chapter, "draft") or ""
                    draft_word_count = runner_validator.count_words(draft_text)
                    if draft_word_count:
                        min_word_count = max(min_word_count, int(draft_word_count * 0.4))

                ok, reason = runner_validator.check_prose_response(content, min_word_count=min_word_count)
                if not ok:
                    fail_dir = runner_renderer.RENDERED_DIR / run_id
                    fail_dir.mkdir(parents=True, exist_ok=True)
                    fail_path = fail_dir / f"ch{chapter:02d}_{storage_step}_rerun_validation_fail.md"
                    fail_path.write_text(content, encoding="utf-8")
                    raise BridgeError(
                        f"Rerun for step '{storage_step}' produced invalid prose output ({reason}). Saved: {fail_path}"
                    )
        except Exception as exc:
            _append_step_failure_event(job_id, str(exc), chapter=chapter, step=storage_step)
            raise

        candidate = _candidate_record(
            chapter=chapter,
            step=storage_step,
            source="rerun",
            content=content,
            steering_note=steering_note.strip(),
        )
        review_required, review_reason, review_status = _review_checkpoint_for_policy(
            review_mode,
            warnings_present=bool(warnings),
        )

        def mutator(updated: dict[str, Any]) -> None:
            candidate_outputs = _ensure_candidate_outputs(updated)
            candidate_outputs.append(candidate)

            step_review = _ensure_review_state(updated, chapter, storage_step)
            step_review.update(
                {
                    "review_required": review_required,
                    "review_reason": review_reason,
                    "review_status": review_status,
                    "approved_candidate_id": None,
                    "last_reviewed_at": None,
                }
            )

        runner_state.update_state(run_id, mutator)
        runner_metrics.record_call(
            run_id,
            chapter,
            storage_step,
            result["model_config"]["model"],
            response,
            content=content,
            extra_fields={
                "attempts": result["attempts"],
                "candidate_id": candidate["candidate_id"],
                "source": "rerun",
            },
        )
        runner_metrics.update_cumulative(_load_run_data(run_id).get("project", "project"), run_id)

        _append_job_event(
            job_id,
            "step_succeeded",
            f"Rerun candidate created: {storage_step}",
            chapter=chapter,
            step=storage_step,
            candidate_id=candidate["candidate_id"],
            review_required=review_required,
            review_mode=review_mode,
            warning_count=len(warnings),
        )
        if review_required:
            _append_job_event(
                job_id,
                "warning",
                "Rerun candidate requires review",
                chapter=chapter,
                step=storage_step,
                candidate_id=candidate["candidate_id"],
                review_mode=review_mode,
                review_reason=review_reason,
                warning_count=len(warnings),
            )
        return {
            "run_id": run_id,
            "chapter": chapter,
            "step": storage_step,
            "candidate_id": candidate["candidate_id"],
            "review_status": review_status,
            "review_required": review_required,
            "warning_count": len(warnings),
        }

    job = _queue_job(
        run_id=run_id,
        job_type="step_rerun",
        target={"run_id": run_id, "chapter": chapter, "step": storage_step},
        worker=worker,
    )
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "candidate_target": {
            "chapter": chapter,
            "step": storage_step,
        },
    }


def update_worksheet_section(run_id: str, section_key: str, content: str) -> dict[str, Any]:
    data = _load_run_data(run_id)
    normalized = content.strip()
    if not normalized:
        raise ValidationBridgeError(
            [{"code": "content_required", "message": "Worksheet section content must not be empty."}]
        )

    try:
        sections = runner_state.parse_sections(data.get("worksheet", ""))
    except Exception as exc:  # pragma: no cover - surfaced through API
        raise BridgeError(str(exc)) from exc

    existing = next((section for section in sections if section["section_key"] == section_key), None)
    if existing is None:
        raise ValidationBridgeError(
            [{"code": "section_not_found", "message": f"Worksheet section not found: {section_key}"}]
        )

    heading = f"## {section_key}"
    new_section_text = normalized if normalized.startswith("## ") else f"{heading}\n\n{normalized}"
    candidate_sections = []
    for section in sections:
        if section["section_key"] == section_key:
            candidate_sections.append({**section, "text": new_section_text})
        else:
            candidate_sections.append(section)

    next_worksheet = runner_state.join_sections(candidate_sections, data.get("worksheet", ""))
    validation = validate_worksheet_text(next_worksheet)
    if not validation["ok"]:
        raise ValidationBridgeError(validation["errors"])

    try:
        runner_state.save_worksheet_section(run_id, section_key, new_section_text)
    except Exception as exc:  # pragma: no cover - surfaced through API
        raise BridgeError(str(exc)) from exc

    return {
        "run_id": run_id,
        "section_key": section_key,
        "status": "saved",
        "worksheet_validation": validation,
    }


def _candidate_record(
    *,
    chapter: int,
    step: str,
    source: str,
    content: str,
    steering_note: str = "",
    status: str = "candidate",
    review_note: str = "",
) -> dict[str, Any]:
    record = {
        "candidate_id": _new_candidate_id(),
        "chapter": chapter,
        "step": step,
        "source": source,
        "steering_note": steering_note,
        "content": content,
        "status": status,
        "created_at": runner_state.now_iso(),
    }
    if review_note:
        record["review_note"] = review_note
    return record


def manual_continue(
    run_id: str,
    chapter: int,
    step: str,
    content: str,
    review_note: str = "",
) -> dict[str, Any]:
    storage_step = _storage_step_name(step)
    _load_run_data(run_id)

    normalized_content = content.strip()
    if not normalized_content:
        raise ValidationBridgeError(
            [{"code": "content_required", "message": "Step content must not be empty."}]
        )

    candidate = _candidate_record(
        chapter=chapter,
        step=storage_step,
        source="manual_edit",
        content=normalized_content,
        status="approved",
        review_note=review_note.strip(),
    )
    reviewed_at = runner_state.now_iso()

    def mutator(data: dict[str, Any]) -> None:
        bucket = data.setdefault("chapters", {}).setdefault(str(chapter), {})
        if not isinstance(bucket, dict):
            raise BridgeError(f"Chapter bucket is invalid: {chapter}")
        bucket[storage_step] = normalized_content

        candidate_outputs = _ensure_candidate_outputs(data)
        candidate_outputs.append(candidate)

        step_review = _ensure_review_state(data, chapter, storage_step)
        step_review.update(
            {
                "review_required": False,
                "review_reason": "manual",
                "review_status": "approved",
                "approved_candidate_id": candidate["candidate_id"],
                "last_reviewed_at": reviewed_at,
            }
        )

    runner_state.update_state(run_id, mutator)
    _sync_summary_and_manuscript_if_needed(run_id, storage_step)

    return {
        "run_id": run_id,
        "chapter": chapter,
        "step": storage_step,
        "candidate_id": candidate["candidate_id"],
        "status": "saved",
    }


def approve_candidate(run_id: str, chapter: int, step: str, candidate_id: str) -> dict[str, Any]:
    data = _load_run_data(run_id)
    storage_step = _storage_step_name(step)
    _validate_step_slot_exists(data, chapter, storage_step)

    studio = data.get("studio", {})
    if not isinstance(studio, dict):
        raise ValidationBridgeError(
            [{"code": "candidate_not_found", "message": f"Candidate not found: {candidate_id}"}]
        )

    candidate_outputs = studio.get("candidate_outputs", [])
    if not isinstance(candidate_outputs, list):
        raise ValidationBridgeError(
            [{"code": "candidate_not_found", "message": f"Candidate not found: {candidate_id}"}]
        )

    target = next(
        (
            candidate
            for candidate in candidate_outputs
            if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id
        ),
        None,
    )
    if target is None:
        raise ValidationBridgeError(
            [{"code": "candidate_not_found", "message": f"Candidate not found: {candidate_id}"}]
        )

    if target.get("chapter") != chapter or target.get("step") != storage_step:
        raise ValidationBridgeError(
            [
                {
                    "code": "candidate_mismatch",
                    "message": "Candidate does not belong to the requested run, chapter, and step.",
                }
            ]
        )

    candidate_content = str(target.get("content", "")).strip()
    if not candidate_content:
        raise ValidationBridgeError(
            [
                {
                    "code": "candidate_empty",
                    "message": f"Candidate content is empty: {candidate_id}",
                }
            ]
        )

    reviewed_at = runner_state.now_iso()

    def mutator(updated: dict[str, Any]) -> None:
        bucket = updated.setdefault("chapters", {}).setdefault(str(chapter), {})
        if not isinstance(bucket, dict):
            raise BridgeError(f"Chapter bucket is invalid: {chapter}")
        bucket[storage_step] = candidate_content

        outputs = _ensure_candidate_outputs(updated)
        for candidate in outputs:
            if not isinstance(candidate, dict):
                continue
            if candidate.get("chapter") != chapter or candidate.get("step") != storage_step:
                continue
            candidate["status"] = "approved" if candidate.get("candidate_id") == candidate_id else "rejected"

        step_review = _ensure_review_state(updated, chapter, storage_step)
        step_review.update(
            {
                "review_required": False,
                "review_reason": step_review.get("review_reason", "manual"),
                "review_status": "approved",
                "approved_candidate_id": candidate_id,
                "last_reviewed_at": reviewed_at,
            }
        )

    runner_state.update_state(run_id, mutator)
    _sync_summary_and_manuscript_if_needed(run_id, storage_step)

    return {
        "run_id": run_id,
        "chapter": chapter,
        "step": storage_step,
        "approved_candidate_id": candidate_id,
        "status": "approved",
    }


def render_step_preview(run_id: str, chapter: int, step: str) -> dict[str, Any]:
    try:
        normalized = runner_renderer.normalize_step_name(step)
        template_name = runner_renderer.template_name_for_step(normalized)
        rendered = runner_renderer.render_step(run_id, chapter, normalized)
    except Exception as exc:  # pragma: no cover - passed through as API 400
        raise BridgeError(str(exc)) from exc

    return {
        "run_id": run_id,
        "chapter": chapter,
        "step": normalized,
        "template_name": template_name,
        "rendered": rendered,
    }


def validate_worksheet_text(content: str) -> dict[str, Any]:
    errors: list[dict[str, str]] = []

    if re.search(r"(?m)^#\s+", content):
        errors.append(
            {
                "code": "worksheet_h1_detected",
                "message": "Worksheet contains H1 headings. Top-level sections must use H2 (`##`).",
            }
        )

    try:
        runner_state.parse_sections(content)
    except Exception as exc:
        errors.append(
            {
                "code": "worksheet_section_parse_failed",
                "message": str(exc),
            }
        )

    try:
        runner_state.extract_required_data_layer(content)
    except Exception as exc:
        errors.append(
            {
                "code": "worksheet_required_data_layer_invalid",
                "message": str(exc),
            }
        )

    return {"ok": not errors, "errors": errors}
