from __future__ import annotations

import copy
import os
import re
import sys
import threading
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


JOBS_LOCK = threading.Lock()
JOBS: dict[str, dict[str, Any]] = {}
ACTIVE_RUN_JOBS: dict[str, str] = {}


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

    return {
        "run_id": run_id,
        "path": _display_path(path),
        "project": data.get("project"),
        "total_chapters": data.get("total_chapters"),
        "current_chapter": current_chapter,
        "latest_completed_step": latest_step,
        "updated_at": data.get("updated_at"),
        "created_at": data.get("created_at"),
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
        result = worker(job_id)
    except Exception as exc:  # pragma: no cover - exercised via API tests instead
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
        return "manual"
    return str(review_policy.get(step) or "manual")


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


def queue_build_manuscript(run_id: str) -> dict[str, Any]:
    def worker(job_id: str) -> dict[str, Any]:
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


def queue_chapter_auto_run(
    run_id: str,
    chapter: int,
    *,
    model_config: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    def worker(job_id: str) -> dict[str, Any]:
        completed_steps: list[str] = []
        for step_name in runner_cli.step_order_for_chapter(chapter):
            canonical_step = _storage_step_name(step_name)
            _append_job_event(
                job_id,
                "step_started",
                f"Step started: {canonical_step}",
                chapter=chapter,
                step=canonical_step,
            )
            runner_cli.execute_step(run_id, chapter, step_name, model_config=model_config, force=force)
            completed_steps.append(canonical_step)
            _append_job_event(
                job_id,
                "step_succeeded",
                f"Step succeeded: {canonical_step}",
                chapter=chapter,
                step=canonical_step,
            )

        manuscript_path: str | None = None
        if "summary" in completed_steps:
            output_path = _build_manuscript_for_run(run_id)
            manuscript_path = _display_path(output_path)

        return {
            "run_id": run_id,
            "chapter": chapter,
            "completed_steps": completed_steps,
            "manuscript_path": manuscript_path,
        }

    return _queue_job(
        run_id=run_id,
        job_type="chapter_auto_run",
        target={"run_id": run_id, "chapter": chapter},
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
    if review_mode not in {"manual", "auto"}:
        raise ValidationBridgeError(
            [{"code": "review_mode_invalid", "message": f"Unsupported review_mode: {review_mode}"}]
        )

    data = _load_run_data(run_id)
    storage_step = _storage_step_name(step)
    _validate_step_slot_exists(data, chapter, storage_step)

    def worker(job_id: str) -> dict[str, Any]:
        _append_job_event(
            job_id,
            "step_started",
            f"Rerun started: {storage_step}",
            chapter=chapter,
            step=storage_step,
        )
        prompt = runner_renderer.render_step(run_id, chapter, storage_step)
        prompt = _steering_prompt(prompt, steering_note)

        result = runner_api.call_step(
            prompt,
            storage_step,
            run_id=run_id,
            chapter=chapter,
            cli_model_config=model_config,
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

        candidate = _candidate_record(
            chapter=chapter,
            step=storage_step,
            source="rerun",
            content=content,
            steering_note=steering_note.strip(),
        )

        def mutator(updated: dict[str, Any]) -> None:
            candidate_outputs = _ensure_candidate_outputs(updated)
            candidate_outputs.append(candidate)

            step_review = _ensure_review_state(updated, chapter, storage_step)
            step_review.update(
                {
                    "review_required": True,
                    "review_reason": "manual" if review_mode == "manual" else "policy",
                    "review_status": "pending",
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
        )
        return {
            "run_id": run_id,
            "chapter": chapter,
            "step": storage_step,
            "candidate_id": candidate["candidate_id"],
            "review_status": "pending",
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
