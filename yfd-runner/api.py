from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable

import requests
from dotenv import load_dotenv
import os
import yaml

import state as state_module

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
MODELS_DIR = BASE_DIR / "models"
CONFIG_PATH = BASE_DIR / "config.yaml"
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(ENV_PATH)


class ApiError(Exception):
    pass


AttemptLogger = Callable[[dict[str, Any]], None]


def normalize_step_name(step_name: str) -> str:
    normalized = step_name.strip().lower().replace("-", "_")
    aliases = {
        "repetition_audit": "repetition",
        "edit_style": "style",
        "edit_craft": "craft",
    }
    return aliases.get(normalized, normalized)


def estimate_prompt_tokens(prompt: str) -> int:
    return len(prompt) // 4


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_model_config(name: str, models_dir: Path | None = None) -> dict[str, Any]:
    path = (models_dir or MODELS_DIR) / f"{name}.yaml"
    if not path.exists():
        raise ApiError(f"Model config not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ApiError(f"Model config is not a mapping: {path}")

    return data


def resolve_model_config(
    step_name: str,
    run_id: str | None = None,
    cli_model_config: str | None = None,
    config_path: Path | None = None,
    models_dir: Path | None = None,
    state_dir: Path | None = None,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    config = state_module.load_config(config_path)
    project = config.get("project", {})
    canonical_step = normalize_step_name(step_name)

    run_override = None
    if run_id:
        try:
            run_override = state_module.load_state(run_id, state_dir).get("model_config")
        except state_module.StateError:
            run_override = None

    step_models = config.get("step_models", {})
    default_name = project.get("default_model_config", "default")
    if run_override == default_name and canonical_step in step_models:
        run_override = None
    selected_name = cli_model_config or run_override or step_models.get(canonical_step) or default_name

    resolved = copy.deepcopy(load_model_config(selected_name, models_dir))
    overrides = (config.get("step_overrides", {}) or {}).get(canonical_step, {})
    if overrides:
        normalized_overrides = copy.deepcopy(overrides)
        if "max_tokens" in normalized_overrides:
            normalized_overrides["max_completion_tokens"] = normalized_overrides.pop("max_tokens")
        resolved = _deep_merge(resolved, normalized_overrides)

    return selected_name, resolved, config


def build_payload(prompt: str, model_config: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(model_config)
    payload["messages"] = [{"role": "user", "content": prompt}]
    return payload


def _extract_response_text(api_response: dict[str, Any]) -> str:
    choices = api_response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def _log_attempt(attempt_logger: AttemptLogger | None, **fields: Any) -> None:
    if attempt_logger:
        attempt_logger(fields)


def post_chat_completion(
    prompt: str,
    model_config: dict[str, Any],
    base_url: str,
    api_key: str,
    timeout: int = 120,
) -> dict[str, Any]:
    payload = build_payload(prompt, model_config)
    response = requests.post(
        base_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )

    try:
        data = response.json()
    except ValueError as exc:
        raise ApiError(f"OpenRouter returned non-JSON response: {response.text[:500]}") from exc

    if response.status_code >= 400:
        message = data.get("error", {}).get("message") or response.text
        raise ApiError(f"OpenRouter error {response.status_code}: {message}")

    return data


def call_step(
    prompt: str,
    step_name: str,
    run_id: str | None = None,
    chapter: int | None = None,
    cli_model_config: str | None = None,
    timeout: int = 120,
    attempt_logger: AttemptLogger | None = None,
    config_path: Path | None = None,
    models_dir: Path | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    selected_name, model_config, config = resolve_model_config(
        step_name,
        run_id=run_id,
        cli_model_config=cli_model_config,
        config_path=config_path,
        models_dir=models_dir,
        state_dir=state_dir,
    )

    env_name = config.get("openrouter", {}).get("api_key_env", "OPENROUTER_API_KEY")
    base_url = config.get("openrouter", {}).get("base_url")
    if not base_url:
        raise ApiError("Missing openrouter.base_url in config.yaml")

    api_key = os.getenv(env_name)
    if not api_key:
        raise ApiError(f"Missing API key in environment variable: {env_name}")

    steps_config = config.get("steps", {}) or {}
    max_retries = int(steps_config.get("max_retries", 0))
    retry_delay_seconds = int(steps_config.get("retry_delay_seconds", 0))
    warn_context_tokens = int(steps_config.get("warn_context_tokens", 0))
    estimated_prompt_tokens = estimate_prompt_tokens(prompt)

    if warn_context_tokens and estimated_prompt_tokens > warn_context_tokens:
        print(
            f"WARNING: estimated prompt tokens for step '{step_name}' are {estimated_prompt_tokens}, "
            f"which exceeds warn_context_tokens={warn_context_tokens}"
        )

    total_attempts = max_retries + 1
    last_error: Exception | None = None

    for attempt in range(1, total_attempts + 1):
        _log_attempt(
            attempt_logger,
            run_id=run_id,
            chapter=chapter,
            step=normalize_step_name(step_name),
            model=selected_name,
            attempt=attempt,
            status="started",
            estimated_prompt_tokens=estimated_prompt_tokens,
        )
        try:
            response = post_chat_completion(prompt, model_config, base_url, api_key, timeout=timeout)
            response_text = _extract_response_text(response).strip()
            if not response_text:
                raise ApiError("OpenRouter returned an empty response body")

            _log_attempt(
                attempt_logger,
                run_id=run_id,
                chapter=chapter,
                step=normalize_step_name(step_name),
                model=selected_name,
                attempt=attempt,
                status="success",
                estimated_prompt_tokens=estimated_prompt_tokens,
            )
            return {
                "response": response,
                "model_config_name": selected_name,
                "model_config": model_config,
                "estimated_prompt_tokens": estimated_prompt_tokens,
                "attempts": attempt,
            }
        except (requests.RequestException, ApiError) as exc:
            last_error = exc
            _log_attempt(
                attempt_logger,
                run_id=run_id,
                chapter=chapter,
                step=normalize_step_name(step_name),
                model=selected_name,
                attempt=attempt,
                status="error",
                error=str(exc),
                estimated_prompt_tokens=estimated_prompt_tokens,
            )
            if attempt >= total_attempts:
                break
            if retry_delay_seconds:
                import time

                time.sleep(retry_delay_seconds)

    raise ApiError(
        f"Step '{step_name}' failed after {total_attempts} attempts: {last_error}"
    )
