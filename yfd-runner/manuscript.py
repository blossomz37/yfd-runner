from __future__ import annotations

from pathlib import Path

import state as state_module

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"


class ManuscriptError(Exception):
    pass


def build_manuscript(run_id: str, output_dir: Path | None = None, state_dir: Path | None = None) -> Path:
    data = state_module.load_state(run_id, state_dir)
    chapters = data.get("chapters", {})
    output_root = output_dir or OUTPUT_DIR
    output_root.mkdir(parents=True, exist_ok=True)

    blocks: list[str] = []
    for chapter_number in sorted(int(key) for key in chapters.keys()):
        final_text = (chapters.get(str(chapter_number), {}).get("final") or "").strip()
        if not final_text:
            continue
        blocks.append(f"# Chapter {chapter_number}\n\n{final_text}")

    output_path = output_root / f"{run_id}_manuscript.md"
    output_path.write_text("\n\n".join(blocks).rstrip() + ("\n" if blocks else ""), encoding="utf-8")
    return output_path
