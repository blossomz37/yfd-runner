# CLAUDE.md

## Project Overview

This repository contains two layers of the same local-first system:

- `yfd-runner`, the Python execution engine for the YFD novel-drafting pipeline
- `YFD Studio`, the FastAPI + Next.js control plane built around that runner

The runner remains canonical. The web app edits and orchestrates the same file-backed workflow rather than replacing it with a second storage model.

## Authoritative Docs

The authoritative product docs live under `SPEC/`:

- `SPEC/SPEC.md` for product direction and UX
- `SPEC/SPEC-requirements.md` for functional requirements and API shape
- `SPEC/SPEC-implementation.md` for implementation notes, scope, and gaps
- `SPEC/CURRENT-STATE.md` for shipped surfaces and the next recommended work

Historical planning notes may live under `.archive/`.

## Repository Layout

```text
.
├── server/                    # FastAPI wrapper and service layer
├── web/                       # Next.js App Router frontend
├── SPEC/                      # Live product and implementation docs
├── .archive/                  # Historical notes and retired planning docs
├── yfd-runner/                # Canonical runner implementation
│   ├── runner.py
│   ├── api.py
│   ├── renderer.py
│   ├── state.py
│   ├── validator.py
│   ├── metrics.py
│   ├── manuscript.py
│   ├── config.yaml
│   ├── models/
│   ├── templates/
│   ├── state/
│   ├── rendered/
│   ├── output/
│   ├── stats/
│   └── test/
├── worksheet-template.md
├── user-commands.md
└── README.md
```

## Tech Stack

- Python 3.13+
- FastAPI for the local backend
- Next.js App Router for the frontend
- Jinja2 for template rendering
- Requests for OpenRouter HTTP calls
- PyYAML for config and model files
- python-dotenv for `.env` loading
- pytest for backend and runner tests

Dependencies:

- Python: `pip install -r requirements.txt`
- Frontend: `cd web && npm install`

## Runtime Setup

Required root `.env` value:

```text
OPENROUTER_API_KEY=<key>
```

Start the backend from the repo root:

```bash
source .venv/bin/activate
uvicorn server.app:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```bash
cd web
npm run dev -- --hostname 127.0.0.1 --port 3001
```

Frontend default API base:

```text
YFD_STUDIO_API_BASE=http://127.0.0.1:8000
```

When the backend is unavailable, the frontend can render read-only fallback data for layout and UI checks. Real writes and live execution still require the backend.

## Core Concepts

Two major workflows:

1. Cascade: fills worksheet sections 2 through 17 from author-provided source material.
2. Chapter loop: `plan -> draft -> repetition -> style -> craft -> final -> summary`.

Important data conventions:

- Run state lives in `yfd-runner/state/<run_id>.json`
- Web-only metadata lives under the top-level `studio` key
- Canonical approved outputs remain in the runner-compatible chapter fields
- Reruns and manual edits are preserved under `studio.candidate_outputs`
- Branch lineage is tracked under `studio.branch`

## Common Commands

Runner commands:

```bash
cd yfd-runner
python runner.py --new --run <run_id> --init --worksheet <path>
python runner.py --run <id> --cascade --section 2
python runner.py --run <id> --cascade --auto
python runner.py --run <id> --chapter 1 --step plan
python runner.py --run <id> --chapter 3 --auto
python runner.py --run <id> --build-manuscript
python runner.py --run <id> --stats
```

Backend tests:

```bash
.venv/bin/pytest -q server/test_app.py
```

Runner tests:

```bash
cd yfd-runner
pytest test/ -v
```

Frontend build:

```bash
cd web
npm run build
```

## Key Behavioral Notes

- Chapter 1 skips the repetition step.
- Job cancellation is cooperative at loop boundaries, not mid-request interruption.
- The current job stream is SSE-compatible over in-memory job records.
- Structured step settings write through `config.step_models` and `config.step_overrides`.
- Raw `config.yaml` editing exists as an advanced surface in addition to structured settings.
