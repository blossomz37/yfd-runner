from __future__ import annotations

import re

DEFAULT_BRACKET_PATTERN = r"\[[A-Z][^\]\n]{15,}\]"
WORD_PATTERN = re.compile(r"\b\w+(?:['-]\w+)?\b")
COMPLETE_SENTENCE_PATTERN = re.compile(r"""[.!?]["')\]]?\s*$""")


class ValidationError(Exception):
    pass


def has_unfilled_brackets(text: str, bracket_pattern: str = DEFAULT_BRACKET_PATTERN) -> bool:
    if re.search(bracket_pattern, text):
        return True
    return re.search(r"\[[^\]]{15,}\]", text, re.DOTALL) is not None


def expected_heading(section_key: str) -> str:
    return f"## {section_key}"


def count_words(text: str) -> int:
    return len(WORD_PATTERN.findall(text or ""))


def check_cascade_response(
    response_text: str,
    expected_section_key: str,
    bracket_pattern: str = DEFAULT_BRACKET_PATTERN,
    min_response_length: int = 50,
) -> tuple[bool, str]:
    text = (response_text or "").strip()
    if len(text) < min_response_length:
        return False, "empty"

    first_nonempty_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if first_nonempty_line != expected_heading(expected_section_key):
        return False, "wrong_section"

    if has_unfilled_brackets(text, bracket_pattern):
        return False, "brackets_remaining"

    return True, "ok"


def check_prose_response(
    response_text: str,
    *,
    min_word_count: int = 500,
) -> tuple[bool, str]:
    text = (response_text or "").strip()
    if count_words(text) < min_word_count:
        return False, "too_short"

    last_nonempty_line = next((line.strip() for line in reversed(text.splitlines()) if line.strip()), "")
    if not COMPLETE_SENTENCE_PATTERN.search(last_nonempty_line):
        return False, "incomplete_ending"

    return True, "ok"
