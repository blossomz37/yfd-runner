# YFD Studio Workspace

This repository is a local workspace for two closely related efforts:

- `yfd-runner`, a Python pipeline for drafting novels with staged prompt workflows
- `YFD Studio`, a planned local-first web UI that will sit on top of the runner

The runner is the current execution engine. The top-level spec documents describe the product and interface direction for the future app.

## Repository Layout

```text
.
├── README.md                  # Root overview and setup
├── SPEC/                      # Product and design specs
│   ├── SPEC.md
│   ├── SPEC-requirements.md
│   ├── SPEC-implementation.md
│   ├── SPEC-CSS-MOCKUPS-v2.md
│   └── SPEC-CSS-MOCKUPS.html
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

## Current Planning Docs

- [SPEC.md](./SPEC/SPEC.md): product spec for the local web control plane
- [SPEC-requirements.md](./SPEC/SPEC-requirements.md): functional requirements and API details
- [SPEC-implementation.md](./SPEC/SPEC-implementation.md): implementation, scope, and delivery notes
- [SPEC-CSS-MOCKUPS-v2.md](./SPEC/SPEC-CSS-MOCKUPS-v2.md): mockup revision brief and notes
- [SPEC-CSS-MOCKUPS.html](./SPEC/SPEC-CSS-MOCKUPS.html): HTML mockups for the selected visual direction

## Setup

This repo does not currently bundle a virtual environment. A clean local setup on macOS is:

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
