from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
RUNNER_DIR = ROOT_DIR / "yfd-runner"
MODELS_DIR = RUNNER_DIR / "models"

if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

import renderer as runner_renderer
import state as runner_state


class BridgeError(Exception):
    """Raised when the service layer cannot fulfill a request."""


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


def _sorted_run_paths() -> list[Path]:
    return sorted(runner_state.STATE_DIR.glob("*.json"))


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
        "path": str(path.relative_to(ROOT_DIR)),
        "project": data.get("project"),
        "total_chapters": data.get("total_chapters"),
        "current_chapter": current_chapter,
        "latest_completed_step": latest_step,
        "updated_at": data.get("updated_at"),
        "created_at": data.get("created_at"),
    }


def list_runs() -> list[dict[str, Any]]:
    return [_run_summary(path) for path in _sorted_run_paths()]


def get_run(run_id: str) -> dict[str, Any]:
    try:
        data = runner_state.load_state(run_id)
    except Exception as exc:  # pragma: no cover - passed through as API 404/400
        raise BridgeError(str(exc)) from exc

    return {
        "run_id": run_id,
        "state_path": str(runner_state.state_path(run_id).relative_to(ROOT_DIR)),
        "data": data,
    }


def list_templates() -> list[dict[str, str]]:
    templates: list[dict[str, str]] = []
    for path in sorted(runner_renderer.TEMPLATES_DIR.glob("*.j2")):
        templates.append(
            {
                "name": path.name,
                "path": str(path.relative_to(ROOT_DIR)),
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
        "path": str(path.relative_to(ROOT_DIR)),
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

    normalized = content if content.endswith("\n") else content + "\n"
    _write_text_atomic(path, normalized)
    return get_template(safe_name)


def list_models() -> list[dict[str, str]]:
    models: list[dict[str, str]] = []
    for path in sorted(MODELS_DIR.glob("*.yaml")):
        models.append(
            {
                "name": path.name,
                "path": str(path.relative_to(ROOT_DIR)),
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
        "path": str(path.relative_to(ROOT_DIR)),
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

    normalized = content if content.endswith("\n") else content + "\n"
    _write_text_atomic(path, normalized)
    return get_model(safe_name)


def get_config() -> dict[str, Any]:
    path = runner_state.CONFIG_PATH
    content = path.read_text(encoding="utf-8")
    data = runner_state.load_config(path)
    return {
        "path": str(path.relative_to(ROOT_DIR)),
        "content": content,
        "data": data,
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
