from __future__ import annotations

from pathlib import Path

import yaml

import api
import state


def test_resolve_model_config_prefers_step_model_for_run_without_override(
    sample_worksheet_path: Path,
    tmp_path: Path,
    tmp_state_dir: Path,
    temp_config_path: Path,
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "default.yaml").write_text(yaml.safe_dump({"model": "openai/default"}), encoding="utf-8")
    (models_dir / "gpt-5.4.yaml").write_text(yaml.safe_dump({"model": "openai/gpt-5.4"}), encoding="utf-8")

    run_id = "routing_new_run"
    state.initialize_run(
        run_id,
        sample_worksheet_path,
        state_dir=tmp_state_dir,
        config_path=temp_config_path,
    )

    selected_name, resolved, _ = api.resolve_model_config(
        "plan",
        run_id=run_id,
        config_path=temp_config_path,
        models_dir=models_dir,
        state_dir=tmp_state_dir,
    )

    assert selected_name == "gpt-5.4"
    assert resolved["model"] == "openai/gpt-5.4"


def test_resolve_model_config_ignores_legacy_default_run_override(
    sample_worksheet_path: Path,
    tmp_path: Path,
    tmp_state_dir: Path,
    temp_config_path: Path,
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "default.yaml").write_text(yaml.safe_dump({"model": "openai/default"}), encoding="utf-8")
    (models_dir / "gpt-5.4.yaml").write_text(yaml.safe_dump({"model": "openai/gpt-5.4"}), encoding="utf-8")

    run_id = "routing_legacy_run"
    state.initialize_run(
        run_id,
        sample_worksheet_path,
        model_config="default",
        state_dir=tmp_state_dir,
        config_path=temp_config_path,
    )

    selected_name, resolved, _ = api.resolve_model_config(
        "plan",
        run_id=run_id,
        config_path=temp_config_path,
        models_dir=models_dir,
        state_dir=tmp_state_dir,
    )

    assert selected_name == "gpt-5.4"
    assert resolved["model"] == "openai/gpt-5.4"


def test_resolve_model_config_honors_explicit_cli_override(
    tmp_path: Path,
    temp_config_path: Path,
) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "claude-sonnet-4.6.yaml").write_text(
        yaml.safe_dump({"model": "anthropic/claude-sonnet-4.6"}),
        encoding="utf-8",
    )

    selected_name, resolved, _ = api.resolve_model_config(
        "plan",
        cli_model_config="claude-sonnet-4.6",
        config_path=temp_config_path,
        models_dir=models_dir,
    )

    assert selected_name == "claude-sonnet-4.6"
    assert resolved["model"] == "anthropic/claude-sonnet-4.6"


def test_resolve_model_config_deep_merges_step_overrides(
    tmp_path: Path,
    temp_config_path: Path,
) -> None:
    config = yaml.safe_load(temp_config_path.read_text(encoding="utf-8"))
    config["step_overrides"]["final"] = {
        "max_tokens": 8000,
        "reasoning": {"effort": "low"},
        "temperature": 0.7,
    }
    temp_config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "gpt-5.4.yaml").write_text(
        yaml.safe_dump(
            {
                "model": "openai/gpt-5.4",
                "reasoning": {"effort": "high", "summary": "auto"},
                "temperature": 1,
                "max_completion_tokens": 128000,
            }
        ),
        encoding="utf-8",
    )

    selected_name, resolved, _ = api.resolve_model_config(
        "final",
        config_path=temp_config_path,
        models_dir=models_dir,
    )

    assert selected_name == "gpt-5.4"
    assert resolved["max_completion_tokens"] == 8000
    assert resolved["temperature"] == 0.7
    assert resolved["reasoning"] == {"effort": "low", "summary": "auto"}
