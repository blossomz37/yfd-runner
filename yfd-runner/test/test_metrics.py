from __future__ import annotations

from pathlib import Path

import metrics
import state


def test_record_call_stores_usage_and_word_count(initialized_run: str, tmp_state_dir: Path) -> None:
    response = {
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 340,
            "total_tokens": 460,
            "cost": 0.0123,
        },
        "choices": [{"message": {"content": "One two three four five."}}],
    }

    record = metrics.record_call(
        initialized_run,
        1,
        "draft",
        "openrouter/openai/gpt-5.4-nano",
        response,
        state_dir=tmp_state_dir,
    )

    assert record["tokens_in"] == 120
    assert record["tokens_out"] == 340
    assert record["word_count"] == 5
    loaded = state.load_state(initialized_run, tmp_state_dir)
    assert loaded["metrics"]["total_tokens_in"] == 120
    assert loaded["metrics"]["total_tokens_out"] == 340
    assert loaded["metrics"]["total_word_count"] == 5


def test_update_cumulative_aggregates_existing_runs(sample_worksheet_path: Path, tmp_state_dir: Path, temp_config_path: Path, tmp_stats_path: Path) -> None:
    for run_id, cost in (("run_a", 0.01), ("run_b", 0.02)):
        state.initialize_run(run_id, sample_worksheet_path, state_dir=tmp_state_dir, config_path=temp_config_path)
        metrics.record_call(
            run_id,
            1,
            "draft",
            "openrouter/openai/gpt-5.4-nano",
            {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "cost": cost,
                },
                "choices": [{"message": {"content": "alpha beta gamma"}}],
            },
            state_dir=tmp_state_dir,
        )

    summary = metrics.update_cumulative("test-project", state_dir=tmp_state_dir, stats_path=tmp_stats_path)
    assert summary["runs"] == ["run_a", "run_b"]
    assert summary["cumulative_tokens_in"] == 20
    assert summary["cumulative_tokens_out"] == 40
    assert summary["cumulative_word_count"] == 6
    assert round(summary["cumulative_cost_usd"], 4) == 0.03


def test_record_call_handles_missing_cost(initialized_run: str, tmp_state_dir: Path) -> None:
    response = {
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 7,
            "total_tokens": 12,
        },
        "choices": [{"message": {"content": "brief output"}}],
    }

    record = metrics.record_call(
        initialized_run,
        1,
        "summary",
        "openrouter/openai/gpt-5.4-nano",
        response,
        state_dir=tmp_state_dir,
    )

    assert record["cost_usd"] is None
    loaded = state.load_state(initialized_run, tmp_state_dir)
    assert loaded["metrics"]["total_cost_usd"] == 0.0
