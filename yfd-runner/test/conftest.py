from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
import yaml

TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

state = importlib.import_module("state")


@pytest.fixture(name="fixtures_dir")
def fixture_fixtures_dir() -> Path:
    return TEST_DIR / "fixtures"


@pytest.fixture(name="sample_worksheet_path")
def fixture_sample_worksheet_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_worksheet.md"


@pytest.fixture(name="sample_response_path")
def fixture_sample_response_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_cascade_section_2_response.md"


@pytest.fixture(name="tmp_state_dir")
def fixture_tmp_state_dir(tmp_path: Path) -> Path:
    path = tmp_path / "state"
    path.mkdir()
    return path


@pytest.fixture(name="tmp_stats_path")
def fixture_tmp_stats_path(tmp_path: Path) -> Path:
    return tmp_path / "stats" / "cumulative.json"


@pytest.fixture(name="temp_config_path")
def fixture_temp_config_path(tmp_path: Path) -> Path:
    config = {
        "openrouter": {
            "api_key_env": "OPENROUTER_API_KEY",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
        },
        "project": {
            "name": "test-project",
            "total_chapters": 6,
            "default_model_config": "default",
        },
        "step_models": {
            "cascade": "gpt-5.2-think",
            "plan": "gpt-5.4",
            "draft": "gpt-5.4",
            "repetition": "gpt-5.4-nano",
            "style": "gpt-5.4-nano",
            "craft": "gpt-5.4-nano",
            "final": "gpt-5.4",
            "summary": "gpt-5.4-nano",
        },
        "step_overrides": {
            "summary": {"max_tokens": 2000, "temperature": 0.3},
        },
        "cascade": {
            "max_retries": 3,
            "retry_delay_seconds": 1,
            "min_response_length": 50,
            "bracket_pattern": state.DEFAULT_BRACKET_PATTERN,
        },
        "steps": {
            "max_retries": 2,
            "retry_delay_seconds": 1,
            "warn_context_tokens": 30000,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture(name="initialized_run")
def fixture_initialized_run(sample_worksheet_path: Path, tmp_state_dir: Path, temp_config_path: Path) -> str:
    run_id = "test_run"
    state.initialize_run(
        run_id,
        sample_worksheet_path,
        state_dir=tmp_state_dir,
        config_path=temp_config_path,
    )
    return run_id
