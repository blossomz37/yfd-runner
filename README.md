# YFD Studio Workspace

This repository contains two closely related pieces of the same local-first system:

- `yfd-runner`, the Python execution engine for the staged novel-drafting pipeline
- `YFD Studio`, the web UI built on top of that runner

The runner remains canonical. YFD Studio is the control plane and editing surface around the existing file-backed workflow.

## Repository Layout

```text
.
├── README.md                  # Root overview and setup
├── server/                    # FastAPI wrapper over yfd-runner
├── web/                       # Next.js frontend app
├── SPEC/                      # Product, requirements, status, and design docs
│   ├── SPEC.md
│   ├── SPEC-requirements.md
│   ├── SPEC-implementation.md
│   ├── CURRENT-STATE.md
│   ├── SPEC-CSS-MOCKUPS-v2.md
│   └── SPEC-CSS-MOCKUPS.html
├── .archive/                  # Historical notes and superseded planning docs
├── CLAUDE.md                  # Working repo notes and command reference
├── worksheet-template.md      # Story worksheet template
├── user-commands.md           # Short command note
└── yfd-runner/                # Python runner and supporting assets
    ├── runner.py
    ├── api.py
    ├── renderer.py
    ├── state.py
    ├── validator.py
    ├── metrics.py
    ├── manuscript.py
    ├── config.yaml
    ├── models/
    ├── templates/
    ├── state/
    ├── rendered/
    ├── output/
    ├── stats/
    └── test/
```

## What `yfd-runner` Does

`yfd-runner` is a file-backed prompt sequencer for a novel-writing pipeline. It renders Jinja templates, calls the OpenRouter API, validates outputs, and persists run state as JSON on disk.

The workflow has two major parts:

1. Cascade: fills worksheet sections 2 through 17 from an author-provided worksheet.
2. Chapter loop: runs `plan -> draft -> repetition -> style -> craft -> final -> summary` for each chapter.

Chapter 1 skips the repetition pass because there are no earlier chapters to compare against.

## Current Product Docs

- [SPEC.md](./SPEC/SPEC.md): product spec for the local web control plane
- [SPEC-requirements.md](./SPEC/SPEC-requirements.md): functional requirements and API details
- [SPEC-implementation.md](./SPEC/SPEC-implementation.md): implementation, scope, and delivery notes
- [CURRENT-STATE.md](./SPEC/CURRENT-STATE.md): shipped surfaces, API status, known gaps, and next recommended work
- [SPEC-CSS-MOCKUPS-v2.md](./SPEC/SPEC-CSS-MOCKUPS-v2.md): mockup revision brief and notes
- [SPEC-CSS-MOCKUPS.html](./SPEC/SPEC-CSS-MOCKUPS.html): HTML mockups for the selected visual direction

## Setup

This repo does not bundle a committed virtual environment. A clean local setup on macOS is:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Required environment variable in the root `.env` file:

```bash
OPENROUTER_API_KEY=<your_key_here>
```

The repo `.gitignore` excludes `.env`, macOS junk files, editor metadata, and Python cache artifacts.

Frontend setup:

```bash
cd web
npm install
```

## Run the App

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

Open:

```text
http://127.0.0.1:3001
```

## Current Shipped Surfaces

The web app currently ships these top-level areas:

- runs dashboard
- intake workspace
- templates
- models
- worksheets
- outputs
- settings
- raw config editor

The run detail surface also includes:

- review and approval controls
- rerun with steering note
- chapter and cascade execution controls
- run-scoped retrieval/search

## Backend Fallback Behavior

The frontend defaults to `YFD_STUDIO_API_BASE=http://127.0.0.1:8000`.

When the backend is unavailable, read surfaces fall back to local demo-safe data so the shell still renders. That fallback is for browsing and layout validation only; real write flows and live runner actions still require the FastAPI backend.

## Common Runner Commands

Run commands from inside `yfd-runner/`:

```bash
cd yfd-runner
```

Create a new run from a worksheet:

```bash
python runner.py --new --run <run_id> --init --worksheet ../worksheet-template.md
```

Fill one cascade section:

```bash
python runner.py --run <run_id> --cascade --section 2
```

Auto-fill remaining cascade sections:

```bash
python runner.py --run <run_id> --cascade --auto
```

Run one chapter step:

```bash
python runner.py --run <run_id> --chapter 1 --step plan
```

Run a full chapter automatically:

```bash
python runner.py --run <run_id> --chapter 3 --auto
```

Render a prompt without calling the API:

```bash
python runner.py --run <run_id> --chapter 3 --step draft --render
```

Rebuild the manuscript:

```bash
python runner.py --run <run_id> --build-manuscript
```

Show run stats:

```bash
python runner.py --run <run_id> --stats
```

For a fuller command reference, see [yfd-runner/user-commands.md](./yfd-runner/user-commands.md).

## Tests

Install dependencies first, then run:

```bash
cd yfd-runner
pytest test/ -v
```

At the moment, running `python3 yfd-runner/runner.py --help` from the repo root fails if dependencies are not installed, because the runner imports `jinja2` at startup.

## Notes on Tracked Files

This repository currently tracks both source files and some generated runner artifacts under:

- `yfd-runner/state/`
- `yfd-runner/rendered/`
- `yfd-runner/output/`
- `yfd-runner/stats/`

If you want a cleaner source-only repository later, those directories should be revisited and some of their contents should likely move to `.gitignore`.
