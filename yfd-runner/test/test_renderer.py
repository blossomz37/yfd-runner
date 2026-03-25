from __future__ import annotations

from pathlib import Path

import renderer
import state

RICH_WORKSHEET = """## section_1_required_data_layer

### required_data_layer
**brain_dump:** Test project.
**target_chapter_count:** 6
**estimated_words_per_chapter:** 2500

## section_2_story_concept

**premise:** Test premise.

## section_8_writing_style_rules

**tense:** past

## section_9_genre_lens

**lens:** thriller

## section_10_story_summary

**summary:** Story summary.

## section_11_structure_breakdown

**act_1:** Setup.

## section_12_chapter_outlines_setup

### chapter_1

**chapter_number:** 1
**chapter_title:** One

### chapter_2

**chapter_number:** 2
**chapter_title:** Two

## section_13_chapter_outlines_rising_action

### chapter_3

**chapter_number:** 3
**chapter_title:** Three
"""


def _seed_chapter(state_dir: Path, run_id: str, chapter: int, final_text: str, summary_text: str = "") -> None:
    state.save_step_output(run_id, chapter, "final", final_text, state_dir)
    if summary_text:
        state.save_step_output(run_id, chapter, "summary", summary_text, state_dir)


def _replace_worksheet(state_dir: Path, run_id: str, worksheet: str) -> None:
    state.update_state(run_id, lambda data: data.__setitem__("worksheet", worksheet), state_dir)


def test_render_plan_first_chapter_branch(initialized_run: str, tmp_state_dir: Path) -> None:
    _replace_worksheet(tmp_state_dir, initialized_run, RICH_WORKSHEET)
    rendered = renderer.render_step(initialized_run, 1, "plan", state_dir=tmp_state_dir)
    assert "This is **Chapter 1**" in rendered
    assert "[Finished Chapter Summaries]" not in rendered
    assert "[Last 3 Chapters]" not in rendered
    assert "## section_12_chapter_outlines_setup" in rendered
    assert "### chapter_1" in rendered
    assert "### chapter_2" not in rendered
    assert "## section_13_chapter_outlines_rising_action" not in rendered


def test_render_plan_non_first_chapter_branch(initialized_run: str, tmp_state_dir: Path) -> None:
    _replace_worksheet(tmp_state_dir, initialized_run, RICH_WORKSHEET)
    state.append_chapter_summary(initialized_run, "## Chapter 1 Summary\nA short summary.", tmp_state_dir)
    state.save_step_output(initialized_run, 1, "final", "Chapter one full text.", tmp_state_dir)

    rendered = renderer.render_step(initialized_run, 2, "plan", state_dir=tmp_state_dir)
    assert "[Finished Chapter Summaries]" in rendered
    assert "[Last 3 Chapters]" in rendered
    assert "This is **Chapter 1**" not in rendered
    assert "Chapter one full text." in rendered
    assert "### chapter_2" in rendered
    assert "### chapter_3" not in rendered


def test_render_draft_uses_trimmed_worksheet(initialized_run: str, tmp_state_dir: Path) -> None:
    _replace_worksheet(tmp_state_dir, initialized_run, RICH_WORKSHEET)
    state.save_step_output(initialized_run, 1, "plan", "A trimmed plan.", tmp_state_dir)

    rendered = renderer.render_step(initialized_run, 1, "draft", state_dir=tmp_state_dir)
    assert "## section_12_chapter_outlines_setup" in rendered
    assert "### chapter_1" in rendered
    assert "### chapter_2" not in rendered
    assert "## section_13_chapter_outlines_rising_action" not in rendered


def test_render_style_uses_only_style_sections(initialized_run: str, tmp_state_dir: Path) -> None:
    _replace_worksheet(tmp_state_dir, initialized_run, RICH_WORKSHEET)
    state.save_step_output(initialized_run, 1, "draft", "Draft text.", tmp_state_dir)

    rendered = renderer.render_step(initialized_run, 1, "style", state_dir=tmp_state_dir)
    assert "## section_8_writing_style_rules" in rendered
    assert "## section_9_genre_lens" in rendered
    assert "## section_10_story_summary" not in rendered
    assert "## section_12_chapter_outlines_setup" not in rendered


def test_render_final_uses_live_style_and_craft_keys(initialized_run: str, tmp_state_dir: Path) -> None:
    _replace_worksheet(tmp_state_dir, initialized_run, RICH_WORKSHEET)
    state.save_step_output(initialized_run, 1, "plan", "Plan text.", tmp_state_dir)
    state.save_step_output(initialized_run, 1, "draft", "Draft text.", tmp_state_dir)
    state.save_step_output(initialized_run, 1, "style", "Style report.", tmp_state_dir)
    state.save_step_output(initialized_run, 1, "craft", "Craft report.", tmp_state_dir)

    rendered = renderer.render_step(initialized_run, 1, "final", state_dir=tmp_state_dir)
    assert "Style report." in rendered
    assert "Craft report." in rendered


def test_build_preceding_chapters_uses_summary_then_full_text(initialized_run: str, tmp_state_dir: Path) -> None:
    _seed_chapter(tmp_state_dir, initialized_run, 1, "Full text one.", "Summary one.")
    _seed_chapter(tmp_state_dir, initialized_run, 2, "Full text two.", "Summary two.")
    _seed_chapter(tmp_state_dir, initialized_run, 3, "Full text three.", "Summary three.")
    _seed_chapter(tmp_state_dir, initialized_run, 4, "Full text four.", "Summary four.")

    text = renderer.build_preceding_chapters(initialized_run, 5, window=3, state_dir=tmp_state_dir)
    assert "**Summary of Chapter 1:**\nSummary one." in text
    assert "## Chapter 2\n\nFull text two." in text
    assert "## Chapter 3\n\nFull text three." in text
    assert "## Chapter 4\n\nFull text four." in text


def test_build_preceding_chapters_early_chapter_uses_full_text_only(initialized_run: str, tmp_state_dir: Path) -> None:
    _seed_chapter(tmp_state_dir, initialized_run, 1, "Full text one.", "Summary one.")
    _seed_chapter(tmp_state_dir, initialized_run, 2, "Full text two.", "Summary two.")

    text = renderer.build_preceding_chapters(initialized_run, 3, window=3, state_dir=tmp_state_dir)
    assert "**Summary of Chapter 1:**" not in text
    assert "## Chapter 1\n\nFull text one." in text
    assert "## Chapter 2\n\nFull text two." in text
