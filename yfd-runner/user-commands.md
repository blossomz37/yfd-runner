# YFD Runner — User Command Reference

All commands are run from inside the `yfd-runner/` directory:

```bash
cd yfd-runner
python runner.py [options]
```

---

## Initialization

### Create a new run from a worksheet file

```bash
python runner.py --new --run <run_id> --init --worksheet <path/to/worksheet.md>
```

---

## Cascade (Worksheet Setup)

Run once per project to fill sections 2–17 of the story worksheet. Section 1 is author-written and not touched by the cascade.

### Fill a single section

```bash
python runner.py --run <run_id> --cascade --section <N>
```

### Auto-fill all remaining sections

```bash
python runner.py --run <run_id> --cascade --auto
```

### Inject manual content into a section (bypasses API call)

```bash
python runner.py --run <run_id> --cascade --section <N> --inject <path/to/file.md>
```

### Check cascade completion status

```bash
python runner.py --run <run_id> --cascade-status
```

---

## Chapter Pipeline

Each chapter runs through these steps in order: `plan → draft → repetition → style → craft → final → summary`

> Note: Chapter 1 skips `repetition` (no prior chapters to compare against).

### Run a single step

```bash
python runner.py --run <run_id> --chapter <N> --step <step_name>
```

### Run all steps for a chapter automatically

```bash
python runner.py --run <run_id> --chapter <N> --auto
```

### Re-run a step that already has output (force overwrite)

```bash
python runner.py --run <run_id> --chapter <N> --step <step_name> --force
```

---

## Render Mode (No API Call)

Renders a prompt template to a `.md` file without making an API call. Useful for inspecting what will be sent to the model.

### Render a chapter step prompt

```bash
python runner.py --run <run_id> --chapter <N> --step <step_name> --render
```

### Render a cascade section prompt

```bash
python runner.py --run <run_id> --step cascade --section <N> --render
```

---

## Stats & Manuscript

### Print token/cost/word-count stats for a run

```bash
python runner.py --run <run_id> --stats
```

### Print cumulative stats across all runs for the project

```bash
python runner.py --run <run_id> --stats --cumulative
```

### Rebuild the combined manuscript file

```bash
python runner.py --run <run_id> --build-manuscript
```

> The manuscript is also rebuilt automatically after every `summary` step.

---

## Step Name Aliases

The `--step` flag accepts both canonical names and aliases:

| Canonical    | Aliases           |
|-------------|-------------------|
| `plan`      | —                 |
| `draft`     | —                 |
| `repetition`| `repetition_audit`|
| `style`     | `edit_style`      |
| `craft`     | `edit_craft`      |
| `final`     | —                 |
| `summary`   | —                 |

---

## Flags Reference

| Flag                    | Description                                                  |
|-------------------------|--------------------------------------------------------------|
| `--run <id>`            | The run ID to operate on (required for almost all commands)  |
| `--chapter <N>`         | Chapter number to work on                                    |
| `--step <name>`         | Step name to execute or render                               |
| `--auto`                | Run all steps/sections automatically                         |
| `--cascade`             | Operate in cascade (worksheet) mode                          |
| `--section <N>`         | Cascade section number (2–17)                                |
| `--render`              | Render prompt to file without making an API call             |
| `--force`               | Skip overwrite prompts and bypass validation                 |
| `--inject <file>`       | Supply manual content for a cascade section                  |
| `--stats`               | Print run stats                                              |
| `--cumulative`          | Combine with `--stats` for project-wide totals               |
| `--cascade-status`      | Show completion status of all cascade sections               |
| `--build-manuscript`    | Rebuild the combined manuscript file                         |
| `--new`                 | Use with `--init` to create a fresh run                      |
| `--init`                | Use with `--new` and `--worksheet` to initialize a run       |
| `--worksheet <path>`    | Path to worksheet file (used with `--new --init`)            |
| `--model-config <name>` | Override the model config for this invocation                |
