# CLAUDE.md

## Project Overview

YFD Runner is a Python-based Jinja2 prompt sequencer for the YFD (Your First Draft) novel-drafting pipeline. It renders prompt templates, calls the OpenRouter API, and manages persistent state across a multi-step chapter-writing workflow.

The current project ("eaw") targets a 25-chapter novel.

## Repository Layout

```
yfd-runner/
  runner.py          # CLI entry point (argparse)
  api.py             # OpenRouter API calls + retry logic
  renderer.py        # Jinja2 template rendering + sliding window assembly
  state.py           # JSON state load/save, cascade status, worksheet ops
  validator.py       # Cascade response validation (brackets, headings)
  metrics.py         # Token/cost/word-count tracking
  manuscript.py      # Builds combined manuscript from chapter finals
  config.yaml        # Model assignments, per-step overrides, cascade settings
  models/            # Named model configs (YAML), one per model
  templates/         # Jinja2 prompt templates (.j2)
  state/             # Per-run JSON state files
  rendered/          # Rendered .md prompts (--render mode)
  output/            # Generated manuscript files
  test/              # pytest suite + fixtures
```

Top-level files: `SPEC.md` is the authoritative project specification. `capability-tests.md` can be ignored.

## Tech Stack

- Python 3.13+
- Jinja2 for template rendering
- Requests for HTTP (OpenRouter API)
- PyYAML for config/model files
- python-dotenv for `.env` loading
- pytest for testing

Dependencies are in `yfd-runner/requirements.txt`. Install with:
```bash
pip install -r yfd-runner/requirements.txt --break-system-packages
```

## Key Concepts

**Two-phase workflow:**

1. **Cascade** — one-time worksheet setup. Sections 2–17 of a 17-section story worksheet are filled iteratively by AI. Section 1 is author-written. Each section builds on the completed ones before it.

2. **Chapter loop** — per-chapter, multi-step pipeline: plan → draft → repetition audit (ch-2+ only) → style edit → craft edit → final → summary. Each step's output feeds into the next.

**State files** (`state/<run_id>.json`) hold everything: worksheet text, per-chapter step outputs, accumulated chapter summaries, and metrics. All state writes use atomic tmp+rename.

**Sliding window** for context: `last_chapters_3` / `last_chapters_5` are built dynamically — recent chapters as full text, older ones as summaries. Prevents context overflow on long projects.

**Model routing** is per-step via `config.yaml` `step_models`. Resolution order: CLI `--model-config` > `step_models[step]` > run-level override > project default > `models/default.yaml`.

## Common CLI Commands

```bash
cd yfd-runner

# Initialize a new run from a worksheet
python runner.py --new --run <run_id> --init --worksheet <path>

# Cascade: fill one section or auto-fill all
python runner.py --run <id> --cascade --section 2
python runner.py --run <id> --cascade --auto

# Chapter: single step or full auto
python runner.py --run <id> --chapter 1 --step plan
python runner.py --run <id> --chapter 3 --auto

# Render-only (no API call)
python runner.py --run <id> --chapter 1 --step plan --render

# Stats and manuscript
python runner.py --run <id> --stats
python runner.py --run <id> --build-manuscript
python runner.py --run <id> --cascade-status
```

## Running Tests

```bash
cd yfd-runner
pytest test/ -v
```

All tests are offline (no API calls). They use fixtures in `test/fixtures/`.

## Environment

The `.env` file lives one directory above `yfd-runner/` (at the project root) and must contain:
```
OPENROUTER_API_KEY=<key>
```

Never hardcode the API key. It is loaded via python-dotenv.

## Step Name Aliases

The `--step` flag and internal code accept these names (aliases resolve automatically):

| Canonical | Aliases |
|-----------|---------|
| `plan` | — |
| `draft` | — |
| `repetition` | `repetition_audit` |
| `style` | `edit_style` |
| `craft` | `edit_craft` |
| `final` | — |
| `summary` | — |

## Cascade Validation

Responses are validated for: minimum length (50 chars), correct section heading (`## section_N_key`), and no remaining `[BRACKETED INSTRUCTION TEXT]` (regex: `\[[A-Z][^\]\n]{15,}\]`). Failures retry up to 3 times, then halt. Use `--force` to bypass validation or `--inject <file>` to supply manual content.

## Important Conventions

- Chapter 1 skips the repetition audit step (no prior chapters to compare against).
- Manuscript is auto-rebuilt after every `summary` step.
- The `step_overrides` section in `config.yaml` fine-tunes temperature and max_tokens per step without changing model assignment.
- Section 1 is excluded from cascade status checks since it's author-written and may legitimately contain brackets.
