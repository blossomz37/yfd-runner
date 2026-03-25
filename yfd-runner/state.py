from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

BASE_DIR = Path(__file__).resolve().parent
STATE_DIR = BASE_DIR / "state"
CONFIG_PATH = BASE_DIR / "config.yaml"
SECTION_HEADING_PATTERN = re.compile(r"^## (section_(\d+)_([^\n]+))\s*$", re.MULTILINE)
DEFAULT_BRACKET_PATTERN = r"\[[A-Z][^\]\n]{15,}\]"


class StateError(Exception):
    pass


def has_unfilled_brackets(text: str, bracket_pattern: str = DEFAULT_BRACKET_PATTERN) -> bool:
    if re.search(bracket_pattern, text):
        return True

    # Some worksheet sections contain a single instruction block spread across multiple lines.
    return re.search(r"\[[^\]]{15,}\]", text, re.DOTALL) is not None


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or CONFIG_PATH
    if not path.exists():
        raise StateError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise StateError(f"Config file is not a mapping: {path}")

    return data


def state_path(run_id: str, state_dir: Path | None = None) -> Path:
    return (state_dir or STATE_DIR) / f"{run_id}.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_metrics() -> dict[str, Any]:
    return {
        "total_tokens_in": 0,
        "total_tokens_out": 0,
        "total_cost_usd": 0.0,
        "total_word_count": 0,
        "calls": [],
    }


def load_state(run_id: str, state_dir: Path | None = None) -> dict[str, Any]:
    path = state_path(run_id, state_dir)
    if not path.exists():
        raise StateError(f"Run state does not exist: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise StateError(f"Run state is not a JSON object: {path}")

    return data


def save_state(run_id: str, data: dict[str, Any], state_dir: Path | None = None) -> Path:
    path = state_path(run_id, state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")

    os.rename(tmp_path, path)
    return path


def parse_sections(worksheet_text: str) -> list[dict[str, Any]]:
    matches = list(SECTION_HEADING_PATTERN.finditer(worksheet_text))
    if not matches:
        raise StateError("Worksheet does not contain any '## section_N_key' headings")

    sections: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(worksheet_text)
        raw_text = worksheet_text[start:end].strip()
        sections.append(
            {
                "section_key": match.group(1),
                "section_number": int(match.group(2)),
                "section_suffix": match.group(3),
                "text": raw_text,
            }
        )

    return sections


def join_sections(sections: list[dict[str, Any]], original_text: str) -> str:
    pieces = [section["text"].rstrip() for section in sections]
    if not pieces:
        return original_text
    return "\n\n".join(pieces).rstrip() + "\n"


def extract_required_data_layer(worksheet_text: str) -> str:
    sections = parse_sections(worksheet_text)
    section_one = next((section for section in sections if section["section_number"] == 1), None)
    if section_one is None:
        raise StateError("Worksheet is missing section_1_required_data_layer")

    match = re.search(
        r"^### required_data_layer\s*$\n(?P<body>.*?)(?=^###\s|\Z)",
        section_one["text"],
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise StateError("Could not find '### required_data_layer' under section 1")

    body = match.group("body").strip()
    if not body:
        raise StateError("The '### required_data_layer' section is empty")

    return body


def initialize_run(
    run_id: str,
    worksheet_path: str | Path,
    model_config: str | None = None,
    state_dir: Path | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    worksheet_file = Path(worksheet_path)
    if not worksheet_file.exists():
        raise StateError(f"Worksheet file does not exist: {worksheet_file}")

    worksheet_text = worksheet_file.read_text(encoding="utf-8").strip() + "\n"
    instructions = extract_required_data_layer(worksheet_text)
    config = load_config(config_path)
    project = config.get("project", {})

    data = {
        "run_id": run_id,
        "project": project.get("name", "project"),
        "model_config": model_config,
        "worksheet": worksheet_text,
        "instructions": instructions,
        "total_chapters": project.get("total_chapters", 0),
        "chapter_summaries": "",
        "metrics": default_metrics(),
        "chapters": {},
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    save_state(run_id, data, state_dir)
    return data


def get_worksheet(run_id: str, state_dir: Path | None = None) -> str:
    return load_state(run_id, state_dir).get("worksheet", "")


def update_state(run_id: str, mutator, state_dir: Path | None = None) -> dict[str, Any]:
    data = load_state(run_id, state_dir)
    updated = deepcopy(data)
    mutator(updated)
    updated["updated_at"] = now_iso()
    save_state(run_id, updated, state_dir)
    return updated


def _chapter_bucket(data: dict[str, Any], chapter: int | str) -> dict[str, Any]:
    chapter_key = str(chapter)
    chapters = data.setdefault("chapters", {})
    bucket = chapters.setdefault(chapter_key, {})
    if not isinstance(bucket, dict):
        raise StateError(f"Chapter bucket is not a mapping: {chapter_key}")
    return bucket


def get_step_output(run_id: str, chapter: int | str, step_name: str, state_dir: Path | None = None) -> str | None:
    data = load_state(run_id, state_dir)
    chapter_data = data.get("chapters", {}).get(str(chapter), {})
    return chapter_data.get(step_name)


def save_step_output(
    run_id: str,
    chapter: int | str,
    step_name: str,
    content: str,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    def mutator(data: dict[str, Any]) -> None:
        bucket = _chapter_bucket(data, chapter)
        bucket[step_name] = content

    return update_state(run_id, mutator, state_dir)


def append_chapter_summary(run_id: str, new_summary: str, state_dir: Path | None = None) -> dict[str, Any]:
    new_summary = new_summary.strip()

    def mutator(data: dict[str, Any]) -> None:
        existing = data.get("chapter_summaries", "").strip()
        if existing:
            data["chapter_summaries"] = existing + "\n\n" + new_summary
        else:
            data["chapter_summaries"] = new_summary

    return update_state(run_id, mutator, state_dir)


def rebuild_chapter_summaries(run_id: str, state_dir: Path | None = None) -> dict[str, Any]:
    def mutator(data: dict[str, Any]) -> None:
        chapters = data.get("chapters", {})
        ordered_summaries: list[str] = []
        for chapter_number in sorted(int(key) for key in chapters.keys()):
            summary_text = (chapters.get(str(chapter_number), {}).get("summary") or "").strip()
            if summary_text:
                ordered_summaries.append(summary_text)
        data["chapter_summaries"] = "\n\n".join(ordered_summaries)

    return update_state(run_id, mutator, state_dir)


def save_worksheet_section(
    run_id: str,
    section_key: str,
    content: str,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    content = content.strip()

    def mutator(data: dict[str, Any]) -> None:
        sections = parse_sections(data.get("worksheet", ""))
        found = False
        for section in sections:
            if section["section_key"] == section_key:
                section["text"] = content
                found = True
                break
        if not found:
            raise StateError(f"Worksheet section not found: {section_key}")
        data["worksheet"] = join_sections(sections, data.get("worksheet", ""))

    return update_state(run_id, mutator, state_dir)


def get_cascade_status(
    run_id: str,
    bracket_pattern: str = DEFAULT_BRACKET_PATTERN,
    state_dir: Path | None = None,
) -> dict[str, str]:
    worksheet = get_worksheet(run_id, state_dir)
    sections = parse_sections(worksheet)
    status: dict[str, str] = {}

    for section in sections:
        number = section["section_number"]
        if number == 1:
            continue
        status[section["section_key"]] = (
            "pending" if has_unfilled_brackets(section["text"], bracket_pattern) else "complete"
        )

    return status


def get_next_incomplete_section(
    run_id: str,
    bracket_pattern: str = DEFAULT_BRACKET_PATTERN,
    state_dir: Path | None = None,
) -> tuple[int, str, str] | None:
    worksheet = get_worksheet(run_id, state_dir)
    sections = parse_sections(worksheet)

    for section in sections:
        if section["section_number"] == 1:
            continue
        if has_unfilled_brackets(section["text"], bracket_pattern):
            return section["section_number"], section["section_key"], section["text"]

    return None


def get_last_chapters(run_id: str, n: int, state_dir: Path | None = None) -> str:
    data = load_state(run_id, state_dir)
    chapters = data.get("chapters", {})
    chapter_numbers = sorted((int(key) for key in chapters.keys()), reverse=True)
    selected: list[str] = []

    for chapter_number in chapter_numbers:
        final_text = chapters.get(str(chapter_number), {}).get("final")
        if final_text:
            selected.append(final_text.strip())
        if len(selected) == n:
            break

    return "\n\n***\n\n".join(reversed(selected))
