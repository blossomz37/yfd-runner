from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import state as state_module

BASE_DIR = Path(__file__).resolve().parent
STATS_DIR = BASE_DIR / "stats"
CUMULATIVE_PATH = STATS_DIR / "cumulative.json"
WORD_PATTERN = re.compile(r"\b\w+(?:['-]\w+)?\b")


class MetricsError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def count_words(text: str) -> int:
    return len(WORD_PATTERN.findall(text or ""))


def _extract_response_text(api_response: dict[str, Any]) -> str:
    choices = api_response.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part)
    return ""


def _coerce_number(value: Any, *, default: int | float | None = None) -> int | float | None:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_money(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:.4f}"


def _atomic_write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    os.rename(tmp_path, path)
    return path


def record_call(
    run_id: str,
    chapter: int | str | None,
    step: str,
    model: str,
    api_response: dict[str, Any],
    content: str | None = None,
    extra_fields: dict[str, Any] | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    usage = api_response.get("usage", {}) or {}
    tokens_in = int(_coerce_number(usage.get("prompt_tokens"), default=0) or 0)
    tokens_out = int(_coerce_number(usage.get("completion_tokens"), default=0) or 0)
    cost_value = _coerce_number(usage.get("cost"), default=None)
    cost_usd = float(cost_value) if cost_value is not None else None
    response_text = content if content is not None else _extract_response_text(api_response)

    record: dict[str, Any] = {
        "chapter": chapter,
        "step": step,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
        "word_count": count_words(response_text),
        "timestamp": now_iso(),
    }
    if extra_fields:
        record.update(extra_fields)

    def mutator(data: dict[str, Any]) -> None:
        metrics = data.setdefault("metrics", state_module.default_metrics())
        metrics.setdefault("calls", []).append(record)
        metrics["total_tokens_in"] = int(metrics.get("total_tokens_in", 0)) + tokens_in
        metrics["total_tokens_out"] = int(metrics.get("total_tokens_out", 0)) + tokens_out
        metrics["total_word_count"] = int(metrics.get("total_word_count", 0)) + record["word_count"]
        if cost_usd is not None:
            metrics["total_cost_usd"] = float(metrics.get("total_cost_usd", 0.0)) + cost_usd
        else:
            metrics.setdefault("total_cost_usd", 0.0)

    updated = state_module.update_state(run_id, mutator, state_dir)
    return record | {"run_metrics": updated.get("metrics", {})}


def update_cumulative(project: str, run_id: str | None = None, state_dir: Path | None = None, stats_path: Path | None = None) -> dict[str, Any]:
    del run_id
    state_root = state_dir or state_module.STATE_DIR
    totals = {
        "project": project,
        "runs": [],
        "cumulative_tokens_in": 0,
        "cumulative_tokens_out": 0,
        "cumulative_cost_usd": 0.0,
        "cumulative_word_count": 0,
        "last_updated": now_iso(),
    }

    if not state_root.exists():
        output_path = stats_path or CUMULATIVE_PATH
        _atomic_write_json(output_path, totals)
        return totals

    for path in sorted(state_root.glob("*.json")):
        data = state_module.load_state(path.stem, state_root)
        if data.get("project") != project:
            continue
        metrics = data.get("metrics", {})
        totals["runs"].append(path.stem)
        totals["cumulative_tokens_in"] += int(metrics.get("total_tokens_in", 0))
        totals["cumulative_tokens_out"] += int(metrics.get("total_tokens_out", 0))
        totals["cumulative_word_count"] += int(metrics.get("total_word_count", 0))
        totals["cumulative_cost_usd"] += float(metrics.get("total_cost_usd", 0.0))

    output_path = stats_path or CUMULATIVE_PATH
    _atomic_write_json(output_path, totals)
    return totals


def print_run_stats(run_id: str, state_dir: Path | None = None) -> str:
    data = state_module.load_state(run_id, state_dir)
    metrics = data.get("metrics", {})
    calls = metrics.get("calls", [])

    lines = [f"Run: {run_id}", "", "Calls:"]
    if not calls:
        lines.append("  (no calls recorded)")
    else:
        for record in calls:
            chapter = record.get("chapter")
            chapter_label = f"ch{chapter}" if chapter is not None else "setup"
            lines.append(
                "  - "
                f"{chapter_label:<7} "
                f"{record.get('step', 'unknown'):<12} "
                f"in={record.get('tokens_in', 0):>6} "
                f"out={record.get('tokens_out', 0):>6} "
                f"words={record.get('word_count', 0):>6} "
                f"cost={_format_money(record.get('cost_usd'))}"
            )

    lines.extend(
        [
            "",
            "Totals:",
            f"  tokens_in:   {metrics.get('total_tokens_in', 0)}",
            f"  tokens_out:  {metrics.get('total_tokens_out', 0)}",
            f"  word_count:  {metrics.get('total_word_count', 0)}",
            f"  cost_usd:    {_format_money(metrics.get('total_cost_usd', 0.0))}",
        ]
    )
    output = "\n".join(lines)
    print(output)
    return output


def print_cumulative_stats(project: str, stats_path: Path | None = None) -> str:
    path = stats_path or CUMULATIVE_PATH
    if not path.exists():
        raise MetricsError(f"Cumulative stats file does not exist: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("project") != project:
        raise MetricsError(
            f"Cumulative stats file is for project '{data.get('project')}', not '{project}'"
        )

    lines = [
        f"Project: {project}",
        f"Runs: {', '.join(data.get('runs', [])) or '(none)'}",
        "",
        "Totals:",
        f"  tokens_in:   {data.get('cumulative_tokens_in', 0)}",
        f"  tokens_out:  {data.get('cumulative_tokens_out', 0)}",
        f"  word_count:  {data.get('cumulative_word_count', 0)}",
        f"  cost_usd:    {_format_money(float(data.get('cumulative_cost_usd', 0.0)))}",
        f"  updated_at:  {data.get('last_updated', 'unknown')}",
    ]
    output = "\n".join(lines)
    print(output)
    return output
