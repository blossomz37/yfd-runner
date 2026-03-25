from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

import state as state_module

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
RENDERED_DIR = BASE_DIR / "rendered"

STEP_TEMPLATE_MAP = {
    "cascade": "00-cascade-worksheet.j2",
    "plan": "01-plan.j2",
    "draft": "02-draft.j2",
    "repetition": "03-repetition-audit.j2",
    "repetition_audit": "03-repetition-audit.j2",
    "style": "04-edit-style.j2",
    "edit_style": "04-edit-style.j2",
    "craft": "05-edit-craft.j2",
    "edit_craft": "05-edit-craft.j2",
    "final": "06-final.j2",
    "summary": "07-summary.j2",
}

STEP_FILE_INDEX = {
    "plan": "01",
    "draft": "02",
    "repetition": "03",
    "repetition_audit": "03",
    "style": "04",
    "edit_style": "04",
    "craft": "05",
    "edit_craft": "05",
    "final": "06",
    "summary": "07",
}


class RendererError(Exception):
    pass


def build_environment(templates_dir: Path | None = None) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_dir or TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        autoescape=False,
        trim_blocks=False,
        lstrip_blocks=False,
    )


def normalize_step_name(step_name: str) -> str:
    normalized = step_name.strip().lower().replace("-", "_")
    if normalized not in STEP_TEMPLATE_MAP:
        raise RendererError(f"Unknown step name: {step_name}")
    return normalized


def template_name_for_step(step_name: str) -> str:
    return STEP_TEMPLATE_MAP[normalize_step_name(step_name)]


def _chapter_numbers(data: dict[str, Any]) -> list[int]:
    return sorted(int(key) for key in data.get("chapters", {}).keys())


def build_preceding_chapters(
    run_id: str,
    current_chapter_n: int,
    window: int = 3,
    state_dir: Path | None = None,
) -> str:
    if current_chapter_n <= 1:
        return ""

    data = state_module.load_state(run_id, state_dir)
    chapters = data.get("chapters", {})
    preceding_numbers = [number for number in _chapter_numbers(data) if number < current_chapter_n]
    if not preceding_numbers:
        return ""

    cutoff = max(1, current_chapter_n - window)
    blocks: list[str] = []

    for chapter_number in preceding_numbers:
        chapter_data = chapters.get(str(chapter_number), {})
        if chapter_number < cutoff:
            summary_text = (chapter_data.get("summary") or "").strip()
            if summary_text:
                blocks.append(f"**Summary of Chapter {chapter_number}:**\n{summary_text}")
            continue

        final_text = (chapter_data.get("final") or "").strip()
        if final_text:
            blocks.append(f"## Chapter {chapter_number}\n\n{final_text}")

    return "\n\n***\n\n".join(blocks)


def _section_by_number(run_id: str, section_number: int, state_dir: Path | None = None) -> dict[str, Any]:
    worksheet = state_module.get_worksheet(run_id, state_dir)
    sections = state_module.parse_sections(worksheet)
    for section in sections:
        if section["section_number"] == section_number:
            return section
    raise RendererError(f"Worksheet section not found: {section_number}")


def _extract_chapter_outline_text(section_text: str, chapter: int) -> str | None:
    heading = f"### chapter_{chapter}"
    pattern = re.compile(
        rf"^{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^### chapter_\d+\s*$|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(section_text)
    if match is None:
        return None

    lines = section_text.splitlines()
    if not lines:
        return None

    return f"{lines[0]}\n\n{heading}\n{match.group('body').strip()}"


def _chapter_step_worksheet(run_id: str, chapter: int, step_name: str, state_dir: Path | None = None) -> str:
    worksheet = state_module.get_worksheet(run_id, state_dir)
    sections = state_module.parse_sections(worksheet)
    normalized_step = normalize_step_name(step_name)

    if normalized_step in {"style", "edit_style"}:
        allowed_numbers = {8, 9}
        selected = [section for section in sections if section["section_number"] in allowed_numbers]
        if not selected:
            return worksheet
        return state_module.join_sections(selected, worksheet)

    if normalized_step not in {"plan", "draft"}:
        return worksheet

    selected = [section for section in sections if section["section_number"] <= 11]
    outline_section = next(
        (
            section
            for section in sections
            if _extract_chapter_outline_text(section["text"], chapter) is not None
        ),
        None,
    )
    if outline_section is None:
        return worksheet

    outline_text = _extract_chapter_outline_text(outline_section["text"], chapter)
    if outline_text is None:
        return worksheet

    selected.append(
        {
            "section_key": outline_section["section_key"],
            "section_number": outline_section["section_number"],
            "section_suffix": outline_section["section_suffix"],
            "text": outline_text,
        }
    )
    return state_module.join_sections(selected, worksheet)


def _step_context(run_id: str, chapter: int, step_name: str, state_dir: Path | None = None) -> dict[str, Any]:
    data = state_module.load_state(run_id, state_dir)
    chapters = data.get("chapters", {})
    chapter_data = chapters.get(str(chapter), {})
    first_chapter = chapter == 1
    style_report = chapter_data.get("edit_style") or chapter_data.get("style", "")
    craft_report = chapter_data.get("edit_craft") or chapter_data.get("craft", "")
    repetition_report = chapter_data.get("repetition_audit") or chapter_data.get("repetition", "")

    return {
        "current_chapter": chapter,
        "total_chapters": data.get("total_chapters", 0),
        "first_chapter": first_chapter,
        "worksheet": _chapter_step_worksheet(run_id, chapter, step_name, state_dir),
        "chapter_summaries": data.get("chapter_summaries", ""),
        "last_chapters_3": build_preceding_chapters(run_id, chapter, window=3, state_dir=state_dir),
        "last_chapters_5": build_preceding_chapters(run_id, chapter, window=5, state_dir=state_dir),
        "plan": chapter_data.get("plan", ""),
        "draft": chapter_data.get("draft", ""),
        "repetition_audit": repetition_report,
        "edit_style": style_report,
        "edit_craft": craft_report,
        "chapter_content": chapter_data.get("final", ""),
        "step_name": normalize_step_name(step_name),
    }


def render_step(
    run_id: str,
    chapter: int,
    step_name: str,
    templates_dir: Path | None = None,
    state_dir: Path | None = None,
) -> str:
    normalized_step = normalize_step_name(step_name)
    environment = build_environment(templates_dir)
    template = environment.get_template(template_name_for_step(normalized_step))
    context = _step_context(run_id, chapter, normalized_step, state_dir)
    return template.render(context)


def render_cascade(
    run_id: str,
    section_number: int,
    templates_dir: Path | None = None,
    state_dir: Path | None = None,
) -> str:
    data = state_module.load_state(run_id, state_dir)
    section = _section_by_number(run_id, section_number, state_dir)
    environment = build_environment(templates_dir)
    template = environment.get_template(template_name_for_step("cascade"))
    context = {
        "instructions": data.get("instructions", ""),
        "total_chapters": data.get("total_chapters", 0),
        "worksheet": data.get("worksheet", ""),
        "context": section["text"],
        "section_number": section_number,
        "section_key": section["section_key"],
    }
    return template.render(context)


def render_to_file(
    run_id: str,
    chapter: int | None,
    step_name: str,
    section_number: int | None = None,
    rendered_dir: Path | None = None,
    templates_dir: Path | None = None,
    state_dir: Path | None = None,
) -> Path:
    normalized_step = normalize_step_name(step_name)
    output_root = rendered_dir or RENDERED_DIR
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if normalized_step == "cascade":
        if section_number is None:
            raise RendererError("section_number is required when rendering the cascade template")
        rendered = render_cascade(run_id, section_number, templates_dir=templates_dir, state_dir=state_dir)
        output_path = run_dir / f"cascade_section_{section_number:02d}.md"
    else:
        if chapter is None:
            raise RendererError("chapter is required when rendering a chapter step")
        rendered = render_step(run_id, chapter, normalized_step, templates_dir=templates_dir, state_dir=state_dir)
        step_index = STEP_FILE_INDEX[normalized_step]
        output_path = run_dir / f"ch{chapter:02d}_step{step_index}_{normalized_step}.md"

    output_path.write_text(rendered, encoding="utf-8")
    return output_path
