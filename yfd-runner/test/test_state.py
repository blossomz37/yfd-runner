from __future__ import annotations

import json
from pathlib import Path

import pytest

import state


def test_initialize_run_roundtrip(initialized_run: str, tmp_state_dir: Path) -> None:
    loaded = state.load_state(initialized_run, tmp_state_dir)
    assert loaded["run_id"] == initialized_run
    assert loaded["project"] == "test-project"
    assert loaded["model_config"] is None
    assert loaded["total_chapters"] == 6
    assert "**brain_dump:**" in loaded["instructions"]
    assert "## section_1_required_data_layer" in loaded["worksheet"]


def test_save_and_get_step_output(initialized_run: str, tmp_state_dir: Path) -> None:
    state.save_step_output(initialized_run, 2, "plan", "plan text", tmp_state_dir)
    assert state.get_step_output(initialized_run, 2, "plan", tmp_state_dir) == "plan text"


def test_save_state_uses_atomic_rename(monkeypatch: pytest.MonkeyPatch, tmp_state_dir: Path) -> None:
    calls: list[tuple[Path, Path]] = []
    real_rename = state.os.rename

    def tracking_rename(src: Path, dst: Path) -> None:
        calls.append((Path(src), Path(dst)))
        real_rename(src, dst)

    monkeypatch.setattr(state.os, "rename", tracking_rename)
    state.save_state("atomic", {"ok": True}, tmp_state_dir)

    assert len(calls) == 1
    src, dst = calls[0]
    assert src.name.endswith(".json.tmp")
    assert dst.name == "atomic.json"


def test_save_worksheet_section_replaces_only_target(initialized_run: str, tmp_state_dir: Path, sample_response_path: Path) -> None:
    replacement = sample_response_path.read_text(encoding="utf-8")
    updated = state.save_worksheet_section(initialized_run, "section_2_story_concept", replacement, tmp_state_dir)
    worksheet = updated["worksheet"]

    assert "### concept_premise" in worksheet
    assert "## section_3_protagonist_operating_systems" in worksheet
    assert "## section_5_story_world" in worksheet
    assert "[Write a sharp concept summary" not in worksheet


def test_get_cascade_status_excludes_section_one(initialized_run: str, tmp_state_dir: Path, sample_response_path: Path) -> None:
    state.save_worksheet_section(
        initialized_run,
        "section_2_story_concept",
        sample_response_path.read_text(encoding="utf-8"),
        tmp_state_dir,
    )
    status = state.get_cascade_status(initialized_run, state_dir=tmp_state_dir)

    assert "section_1_required_data_layer" not in status
    assert status["section_2_story_concept"] == "complete"
    assert status["section_3_protagonist_operating_systems"] == "pending"


def test_get_next_incomplete_section_returns_first_pending(initialized_run: str, tmp_state_dir: Path, sample_response_path: Path) -> None:
    section_2 = sample_response_path.read_text(encoding="utf-8")
    section_3 = "## section_3_protagonist_operating_systems\n\n### core_fear\nExposure.\n"
    state.save_worksheet_section(initialized_run, "section_2_story_concept", section_2, tmp_state_dir)
    state.save_worksheet_section(initialized_run, "section_3_protagonist_operating_systems", section_3, tmp_state_dir)

    next_section = state.get_next_incomplete_section(initialized_run, state_dir=tmp_state_dir)

    assert next_section is not None
    assert next_section[0] == 5
    assert next_section[1] == "section_5_story_world"


def test_load_state_roundtrip_file_contents(tmp_state_dir: Path) -> None:
    payload = {"run_id": "manual", "project": "test-project", "metrics": {}, "chapters": {}}
    path = state.save_state("manual", payload, tmp_state_dir)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["run_id"] == "manual"
    assert state.load_state("manual", tmp_state_dir)["project"] == "test-project"


def test_rebuild_chapter_summaries_uses_saved_summary_steps(initialized_run: str, tmp_state_dir: Path) -> None:
    state.save_step_output(initialized_run, 1, "summary", "## Chapter 1 Summary\nFresh one", tmp_state_dir)
    state.save_step_output(initialized_run, 2, "summary", "## Chapter 2 Summary\nFresh two", tmp_state_dir)
    state.append_chapter_summary(initialized_run, "## Chapter 1 Summary\nStale one", tmp_state_dir)

    updated = state.rebuild_chapter_summaries(initialized_run, tmp_state_dir)

    assert updated["chapter_summaries"] == "## Chapter 1 Summary\nFresh one\n\n## Chapter 2 Summary\nFresh two"
