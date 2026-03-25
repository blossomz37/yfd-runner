from __future__ import annotations

import validator


def test_check_cascade_response_ok(sample_response_path) -> None:
    response = sample_response_path.read_text(encoding="utf-8")
    assert validator.check_cascade_response(response, "section_2_story_concept") == (True, "ok")


def test_check_cascade_response_brackets_remaining() -> None:
    response = "## section_2_story_concept\n[FILL IN PROTAGONIST NAME HERE]"
    assert validator.check_cascade_response(response, "section_2_story_concept") == (False, "brackets_remaining")


def test_check_cascade_response_empty() -> None:
    assert validator.check_cascade_response("", "section_2_story_concept") == (False, "empty")


def test_check_cascade_response_wrong_section() -> None:
    response = "## section_3_protagonist_operating_systems\nFilled body content that is long enough to avoid empty handling."
    assert validator.check_cascade_response(response, "section_2_story_concept") == (False, "wrong_section")


def test_check_prose_response_ok() -> None:
    response = ("This is a complete sentence. " * 300).strip()
    assert validator.check_prose_response(response, min_word_count=500) == (True, "ok")


def test_check_prose_response_too_short() -> None:
    response = "Too short."
    assert validator.check_prose_response(response, min_word_count=10) == (False, "too_short")


def test_check_prose_response_incomplete_ending() -> None:
    response = ("This is a complete sentence. " * 200) + "This last sentence stops"
    assert validator.check_prose_response(response, min_word_count=500) == (False, "incomplete_ending")
