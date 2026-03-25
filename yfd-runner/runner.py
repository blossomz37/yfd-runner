from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import api
import manuscript
import metrics
import renderer
import state
import validator

CHAPTER_STEP_ORDER = ["plan", "draft", "repetition", "style", "craft", "final", "summary"]
FIRST_CHAPTER_STEP_ORDER = ["plan", "draft", "style", "craft", "final", "summary"]


class RunnerError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YFD Runner")
    parser.add_argument("--run")
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--step")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--cascade", action="store_true")
    parser.add_argument("--section", type=int)
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--cumulative", action="store_true")
    parser.add_argument("--build-manuscript", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--inject")
    parser.add_argument("--cascade-status", action="store_true")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--new", action="store_true")
    parser.add_argument("--worksheet")
    parser.add_argument("--model-config")
    return parser.parse_args()


def canonical_step_name(step_name: str) -> str:
    return renderer.normalize_step_name(step_name)


def step_order_for_chapter(chapter: int) -> list[str]:
    return FIRST_CHAPTER_STEP_ORDER if chapter == 1 else CHAPTER_STEP_ORDER


def project_name_from_run(run_id: str) -> str:
    return state.load_state(run_id).get("project", "project")


def print_cascade_status(run_id: str) -> str:
    status = state.get_cascade_status(run_id)
    lines = [f"Run: {run_id}", "", "Sections:", "  - section_1_required_data_layer: author-filled"]
    for section_key, section_status in status.items():
        lines.append(f"  - {section_key}: {section_status}")
    output = "\n".join(lines)
    print(output)
    return output


def maybe_prompt_overwrite(run_id: str, chapter: int, step_name: str, force: bool = False) -> None:
    existing = state.get_step_output(run_id, chapter, step_name)
    if not existing or force:
        return

    reply = input(f"Output already exists for run={run_id} chapter={chapter} step={step_name}. Overwrite? [y/N] ")
    if reply.strip().lower() not in {"y", "yes"}:
        raise RunnerError("Aborted to avoid overwriting existing step output")


def append_attempt_error(run_id: str | None, payload: dict[str, Any]) -> None:
    if not run_id:
        return
    if payload.get("status") != "error":
        return

    def mutator(data: dict[str, Any]) -> None:
        metrics_block = data.setdefault("metrics", state.default_metrics())
        metrics_block.setdefault("calls", []).append(
            {
                "chapter": payload.get("chapter"),
                "step": payload.get("step"),
                "model": payload.get("model"),
                "attempt": payload.get("attempt"),
                "status": payload.get("status"),
                "error": payload.get("error"),
                "estimated_prompt_tokens": payload.get("estimated_prompt_tokens"),
                "timestamp": metrics.now_iso(),
            }
        )

    state.update_state(run_id, mutator)


def execute_step(run_id: str, chapter: int, step_name: str, model_config: str | None = None, force: bool = False) -> str:
    canonical = canonical_step_name(step_name)
    maybe_prompt_overwrite(run_id, chapter, canonical, force=force)
    prompt = renderer.render_step(run_id, chapter, canonical)
    result = api.call_step(
        prompt,
        canonical,
        run_id=run_id,
        chapter=chapter,
        cli_model_config=model_config,
        attempt_logger=lambda payload: append_attempt_error(run_id, payload),
    )
    response = result["response"]
    content = response["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "\n".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
    content = str(content).strip()

    if canonical in {"draft", "final"}:
        min_word_count = 500
        if canonical == "final":
            draft_text = state.get_step_output(run_id, chapter, "draft") or ""
            draft_word_count = validator.count_words(draft_text)
            if draft_word_count:
                min_word_count = max(min_word_count, int(draft_word_count * 0.4))

        ok, reason = validator.check_prose_response(content, min_word_count=min_word_count)
        if not ok:
            fail_dir = renderer.RENDERED_DIR / run_id
            fail_dir.mkdir(parents=True, exist_ok=True)
            fail_path = fail_dir / f"ch{chapter:02d}_{canonical}_validation_fail.md"
            fail_path.write_text(content, encoding="utf-8")
            raise RunnerError(
                f"Step '{canonical}' produced invalid prose output ({reason}). Saved: {fail_path}"
            )

    state.save_step_output(run_id, chapter, canonical if canonical != "repetition" else "repetition_audit", content)
    metrics.record_call(
        run_id,
        chapter,
        canonical,
        result["model_config"]["model"],
        response,
        content=content,
        extra_fields={"attempts": result["attempts"]},
    )
    metrics.update_cumulative(project_name_from_run(run_id), run_id)

    if canonical == "summary":
        state.rebuild_chapter_summaries(run_id)
        manuscript.build_manuscript(run_id)

    return content


def render_command(run_id: str, chapter: int | None, step_name: str | None, section_number: int | None = None) -> Path:
    if step_name == "cascade":
        return renderer.render_to_file(run_id, None, "cascade", section_number=section_number)
    if chapter is None or step_name is None:
        raise RunnerError("chapter and step are required for render mode")
    return renderer.render_to_file(run_id, chapter, step_name)


def handle_cascade(run_id: str, args: argparse.Namespace) -> None:
    if args.inject and not args.section:
        raise RunnerError("--inject requires --section")

    if args.auto:
        while True:
            next_section = state.get_next_incomplete_section(run_id)
            if next_section is None:
                print("Cascade complete")
                return
            section_number = next_section[0]
            run_cascade_section(run_id, section_number, args)

    if args.section is None:
        raise RunnerError("--section is required unless using --cascade --auto")

    run_cascade_section(run_id, args.section, args)


def run_cascade_section(run_id: str, section_number: int, args: argparse.Namespace) -> None:
    section = state.parse_sections(state.get_worksheet(run_id))
    target = next((item for item in section if item["section_number"] == section_number), None)
    if target is None:
        raise RunnerError(f"Unknown worksheet section: {section_number}")

    if args.render:
        path = renderer.render_to_file(run_id, None, "cascade", section_number=section_number)
        print(path)
        return

    if args.inject:
        content = Path(args.inject).read_text(encoding="utf-8").strip()
        state.save_worksheet_section(run_id, target["section_key"], content)
        print(f"Injected {target['section_key']}")
        return

    prompt = renderer.render_cascade(run_id, section_number)
    result = api.call_step(
        prompt,
        "cascade",
        run_id=run_id,
        cli_model_config=args.model_config,
        attempt_logger=lambda payload: append_attempt_error(run_id, payload),
    )
    response = result["response"]
    content = response["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "\n".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
    content = str(content).strip()

    if not args.force:
        config = state.load_config()
        cascade_config = config.get("cascade", {})
        ok, reason = validator.check_cascade_response(
            content,
            target["section_key"],
            bracket_pattern=cascade_config.get("bracket_pattern", validator.DEFAULT_BRACKET_PATTERN),
            min_response_length=int(cascade_config.get("min_response_length", 50)),
        )
        if not ok:
            fail_path = renderer.RENDERED_DIR / run_id
            fail_path.mkdir(parents=True, exist_ok=True)
            output_path = fail_path / f"cascade_fail_section_{section_number:02d}_{target['section_key']}.md"
            output_path.write_text(content, encoding="utf-8")
            raise RunnerError(f"Cascade validation failed for {target['section_key']}: {reason}. Saved: {output_path}")

    state.save_worksheet_section(run_id, target["section_key"], content)
    metrics.record_call(
        run_id,
        None,
        "cascade",
        result["model_config"]["model"],
        response,
        content=content,
        extra_fields={"attempts": result["attempts"], "section": target["section_key"]},
    )
    metrics.update_cumulative(project_name_from_run(run_id), run_id)
    print(f"Completed {target['section_key']}")


def handle_chapter(run_id: str, args: argparse.Namespace) -> None:
    if args.chapter is None:
        raise RunnerError("--chapter is required for chapter execution")

    chapter = args.chapter

    if args.render:
        if not args.step:
            raise RunnerError("--step is required with --render for chapter mode")
        print(renderer.render_to_file(run_id, chapter, args.step))
        return

    if args.auto:
        for step_name in step_order_for_chapter(chapter):
            execute_step(run_id, chapter, step_name, model_config=args.model_config, force=args.force)
        return

    if not args.step:
        raise RunnerError("--step is required unless using --auto")

    execute_step(run_id, chapter, args.step, model_config=args.model_config, force=args.force)


def main() -> None:
    args = parse_args()

    if args.new and args.init:
        if not args.run or not args.worksheet:
            raise RunnerError("--new --init requires --run and --worksheet")
        run_state = state.initialize_run(args.run, args.worksheet, model_config=args.model_config)
        print(f"Initialized {args.run} with {len(run_state['instructions'])} instruction chars")
        return

    if args.stats and args.cumulative:
        project = project_name_from_run(args.run) if args.run else state.load_config().get("project", {}).get("name", "project")
        metrics.update_cumulative(project)
        metrics.print_cumulative_stats(project)
        return

    if args.stats:
        if not args.run:
            raise RunnerError("--stats requires --run")
        metrics.print_run_stats(args.run)
        return

    if args.build_manuscript:
        if not args.run:
            raise RunnerError("--build-manuscript requires --run")
        print(manuscript.build_manuscript(args.run))
        return

    if args.cascade_status:
        if not args.run:
            raise RunnerError("--cascade-status requires --run")
        print_cascade_status(args.run)
        return

    if args.cascade:
        if not args.run:
            raise RunnerError("--cascade requires --run")
        handle_cascade(args.run, args)
        return

    if args.render and args.step == "cascade":
        if not args.run or args.section is None:
            raise RunnerError("Cascade render requires --run --step cascade --section N")
        print(render_command(args.run, None, "cascade", section_number=args.section))
        return

    if args.chapter or args.step or args.auto or args.render:
        if not args.run:
            raise RunnerError("Chapter operations require --run")
        handle_chapter(args.run, args)
        return

    raise RunnerError("No operation selected")


if __name__ == "__main__":
    try:
        main()
    except RunnerError as exc:
        raise SystemExit(str(exc)) from exc
