# YFD Studio — Preliminary Product Spec

**Project:** Web application for authoring, running, and inspecting the YFD pipeline  
**Working name:** `YFD Studio`  
**Repository root:** `/Users/carlo/claude-cowork-ghost-draft-npe`  
**Status:** Preliminary draft for iteration

---

## 1. Product Summary

YFD Studio is a polished local-first web app that sits on top of the existing `yfd-runner` Python pipeline.

It should let a user:
- edit prompt templates in [`yfd-runner/templates`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/templates)
- edit model configs in [`yfd-runner/models`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/models)
- inspect and edit run state in [`yfd-runner/state`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/state)
- launch cascade and chapter steps
- watch run progress live
- inspect rendered prompts, responses, metrics, and validation failures

The existing CLI runner remains the execution engine and source of truth. The web app is a control plane and editor layer, not a parallel implementation of the workflow.

---

## 2. Goals

### Primary goals

- Make the YFD pipeline operable without terminal fluency.
- Make prompts and model settings editable from a serious UI, not raw shell commands.
- Expose run state clearly enough that users can understand what the pipeline is doing while it is running.
- Preserve compatibility with the current file-backed runner.
- Keep the architecture simple enough to ship quickly.

### Non-goals for v1

- Multi-user collaboration
- cloud deployment as the primary mode
- replacing the existing JSON/file-backed storage with a database
- changing the underlying generation workflow semantics
- visual no-code prompt composition

---

## 3. Product Principles

- The runner stays canonical. Web actions call into the same logic used by the CLI.
- File-backed first. The app edits the existing files in place instead of creating a hidden second system.
- Preview before mutation. Templates and configs should support validation and preview before save.
- Progress must be visible. Long-running steps need explicit live status, not silent waiting.
- Failures must be inspectable. If a step fails, the user should see why, where, and what file was produced.

---

## 4. Users and Core Jobs

### Primary user

An author or operator running the YFD novel pipeline locally on their own machine.

### Core jobs

- Start a new run from a worksheet file.
- Start a new project from a story dossier or loose notes.
- Resume an interrupted run.
- Run one cascade section or one chapter step.
- Run a whole chapter automatically.
- Edit a Jinja prompt template and immediately preview the rendered result for a chosen run/chapter.
- Change model routing or token settings without opening YAML in a terminal editor.
- Inspect chapter outputs and see which step last succeeded or failed.
- Review, approve, reject, or rerun outputs without dropping to the terminal.
- Branch a run and compare different prompt, model, or steering choices.

---

## 5. Existing System Constraints

The current codebase is Python-only and already contains the essential execution modules:
- [`yfd-runner/runner.py`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/runner.py): orchestration and CLI entry point
- [`yfd-runner/renderer.py`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/renderer.py): Jinja rendering and step context assembly
- [`yfd-runner/api.py`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/api.py): OpenRouter request execution
- [`yfd-runner/state.py`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/state.py): run state persistence
- [`yfd-runner/metrics.py`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/metrics.py): per-run and cumulative metrics
- [`yfd-runner/validator.py`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/validator.py): output validation

The web app should reuse these modules directly where practical.

---

## 6. Recommended Architecture

### Frontend

- `Next.js`
- TypeScript
- App Router
- `CodeMirror 6` for text editing
- Tailwind or CSS modules for the first pass
- SSE client for live run updates

### Backend

- `FastAPI`
- direct imports from `yfd-runner` modules where safe
- background job manager for long-running steps
- SSE endpoint for progress streaming

### Why this architecture

`FastAPI` matches the existing Python runner and avoids wrapping core logic in shell-only calls. `Next.js` is the fastest path to a polished application shell, routing, and good editor ergonomics. This split also keeps the product extensible if a database or remote deployment is needed later.

---

## 7. High-Level System Design

```text
Browser UI
  -> Next.js frontend
  -> FastAPI backend
  -> yfd-runner modules
  -> filesystem under yfd-runner/
       templates/
       models/
       state/
       rendered/
       output/
       stats/
```

### Execution model

- The frontend requests a run action.
- The backend creates a job record in memory.
- The backend calls the existing runner logic directly, step by step.
- Progress events are streamed to the frontend over SSE.
- Outputs continue to be written to the existing files under `yfd-runner/`.

---

## 8. UI Information Architecture

### Main areas

- `Runs`
- `Intake`
- `Templates`
- `Models`
- `Worksheets`
- `Outputs`
- `Settings`

### Proposed layout

- left sidebar: top-level navigation plus run list
- main panel: editor, detail view, or dashboard
- right rail: metadata, validation, token estimate, step actions

### Key screens

#### 8.1 Runs Dashboard

Shows:
- all known runs from [`yfd-runner/state`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/state)
- current chapter and latest completed step
- total tokens, cost, and word count
- current job status if a run is active

Actions:
- create run
- resume run
- open run detail
- build manuscript

#### 8.1.1 Create Run Modal

Shows:
- run id input
- worksheet file picker
- model config selector
- optional output directory picker

Behavior:
- validates the selected worksheet before creating the run
- blocks submission if worksheet structure is invalid
- surfaces validation errors inline before any state file is created

#### 8.1.2 Create Project Wizard

Entry choices:
- `Worksheet`
- `Story dossier`
- `Loose notes`

Behavior:
- `Worksheet` path follows the direct run-creation flow
- `Story dossier` path opens dossier import, extraction, mapping, and confirmation
- `Loose notes` path opens a normalization step before worksheet generation

#### 8.1.3 Branch Run Modal

Shows:
- source run id
- new run id
- optional chapter cutoff
- optional notes describing the experiment

Behavior:
- copies the source run state into a new branch run
- preserves lineage metadata for comparison views
- allows the user to test new templates, model configs, or steering notes without overwriting the source run

#### 8.2 Run Detail

Shows:
- run metadata
- chapter-by-chapter grid
- per-step status for each chapter
- recent call history
- current worksheet snapshot

Actions:
- run a single step
- run a full chapter
- force rerun a step
- inspect failure output

#### 8.3 Template Editor

Shows:
- list of files in [`yfd-runner/templates`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/templates)
- syntax-highlighted editor
- template preview panel
- warnings for undefined variables or render errors

Actions:
- save
- render preview for selected run/chapter
- diff against last saved version in session

#### 8.4 Model Editor

Shows:
- list of YAML model configs in [`yfd-runner/models`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/models)
- parsed form plus raw YAML mode
- effective settings after step overrides

Actions:
- save
- validate YAML
- compare model configs

#### 8.5 Worksheet Explorer

Shows:
- section list from `parse_sections`
- raw worksheet content
- structured section view

Actions:
- jump to section
- edit section text
- save section

#### 8.5.1 Intake Workspace

Shows:
- imported source files and pasted text blocks
- detected input type and extraction summary
- mapping between source material and worksheet destinations
- unresolved fields or ambiguous mappings

Actions:
- upload files
- paste raw text
- normalize input
- accept or edit proposed mappings
- generate initial worksheet draft

#### 8.6 Output Inspector

Shows:
- rendered prompt
- model response
- validation result
- metrics for the call
- saved output for plan, draft, style, craft, final, or summary

Actions:
- approve output
- reject output
- rerun output
- rerun with steering note
- edit output manually and continue

#### 8.7 Comparison View

Shows:
- side-by-side outputs from two runs or two reruns
- metadata differences such as model config, template version, and steering note
- diff view for prompt and output text

Actions:
- mark preferred version
- promote a branch as the new working run

---

## 9. Functional Requirements

### 9.1 File Editing

The app must support direct editing of:
- template files under `templates/`
- model YAML files under `models/`
- config file [`yfd-runner/config.yaml`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/config.yaml)
- worksheet content stored in run state

Requirements:
- server-side validation before save
- clear error reporting
- no partial writes
- explicit dirty-state indication in the UI

### 9.1.1 Worksheet Import Validation

When the user selects a worksheet file to create a run, the backend must validate:
- the file exists and is readable
- the worksheet contains `## section_N_key` headings
- the worksheet contains `## section_1_required_data_layer`
- the worksheet contains `### required_data_layer` under section 1
- the worksheet contains no `# ` H1 headings anywhere in the file

Validation rule:
- top-level worksheet sections must be H2 headings, not H1 headings

Failure behavior:
- the UI must show a clear message such as "Worksheet contains H1 headings. Top-level sections must use H2 (`##`)."
- the run must not be created until the file passes validation

### 9.1.2 Story Dossier Intake

The app must support project creation from semi-structured source material, not only prebuilt worksheets.

Supported v1 dossier inputs:
- pasted markdown or plain text
- uploaded markdown or text files
- multiple input blocks in one project intake session

Deferred inputs:
- DOCX
- PDF
- web clipping and URL import

The intake flow must support:
- source labeling such as `brain dump`, `synopsis`, `character notes`, `world notes`, `beat sheet`
- text extraction into normalized internal blocks
- user review before worksheet generation

### 9.1.3 Input Normalization and Mapping

When the user imports a story dossier or loose notes, the backend must:
- preserve the raw imported text
- create normalized text blocks for downstream processing
- propose mappings from source blocks into worksheet destinations

Initial worksheet destinations include:
- section 1 required data layer
- story concept
- protagonist operating systems
- supporting cast
- story world
- genre lens
- chapter outline inputs

The user must be able to:
- accept the proposed mapping
- edit the mapping
- remove irrelevant source blocks
- continue with a generated worksheet draft

### 9.1.3.1 Locked V1 Dossier Target Taxonomy

To avoid vague or arbitrary mapping behavior, v1 should map dossier material into a small explicit target set.

Locked v1 targets:
- `section_1.required_data_layer`
- `section_2.story_concept`
- `section_3.protagonist_operating_systems`
- `section_4.supporting_cast`
- `section_5.story_world`
- `section_8.writing_style_rules`
- `section_9.genre_lens`
- `chapter_outline_inputs`

Input-label routing defaults:
- `brain_dump` -> `section_1.required_data_layer`
- `synopsis` -> `section_2.story_concept`
- `character_notes` -> `section_3.protagonist_operating_systems`
- `supporting_cast` -> `section_4.supporting_cast`
- `world_notes` -> `section_5.story_world`
- `style_notes` -> `section_8.writing_style_rules`
- `genre_notes` -> `section_9.genre_lens`
- `beat_sheet` -> `chapter_outline_inputs`

Rules:
- a block may map to more than one target
- the user may override default mappings before worksheet generation
- unmapped blocks remain preserved in `studio.dossier_blocks`

Out of scope for v1:
- automatic mapping into sections 6, 7, and 10 through 17 with high confidence claims
- ontology-level extraction of every field in the worksheet

### 9.1.4 Internal Data Model

The web app requires a small service-layer data model that the current CLI runner does not define.

V1 persistence strategy:
- preserve the current runner-compatible run JSON shape
- add web-app-specific metadata under a top-level `studio` key in each run state file
- avoid changing existing runner keys unless necessary for compatibility

#### `studio.run_settings`

Purpose:
- persist user-facing run configuration that the current runner does not track

Fields:
- `output_dir`: absolute path string or `null`
- `review_policy`: object keyed by step name
- `default_steering_note`: string or empty string
- `created_from`: `worksheet` | `dossier` | `loose_notes`

#### `studio.dossier_blocks`

Purpose:
- preserve imported source material and normalized forms before worksheet generation

Fields per block:
- `block_id`: stable string id
- `label`: user or system label such as `brain_dump` or `character_notes`
- `source_type`: `pasted_text` | `uploaded_markdown` | `uploaded_text`
- `source_name`: original filename or user label
- `raw_text`: original imported text
- `normalized_text`: cleaned text used for mapping
- `included`: boolean
- `mapping_targets`: array of target ids such as `section_1.required_data_layer`
- `created_at`: ISO timestamp

#### `studio.review_state`

Purpose:
- track whether a step is awaiting human review before loop continuation

Fields per chapter/step:
- `review_required`: boolean
- `review_reason`: `policy` | `warning` | `failure` | `manual`
- `review_status`: `not_required` | `pending` | `approved` | `rejected`
- `approved_candidate_id`: string or `null`
- `last_reviewed_at`: ISO timestamp or `null`

#### `studio.candidate_outputs`

Purpose:
- preserve reruns and manual edits without immediately overwriting the canonical saved step output

Fields per candidate:
- `candidate_id`: stable string id
- `chapter`: integer
- `step`: canonical step name
- `source`: `initial_run` | `rerun` | `manual_edit`
- `steering_note`: string or empty string
- `content`: full text
- `status`: `candidate` | `approved` | `rejected`
- `created_at`: ISO timestamp

Canonical rule:
- the runner-compatible chapter field such as `chapters["3"]["draft"]` remains the canonical approved output
- candidate outputs are promoted into canonical fields only on approval or manual continue

#### `studio.branch`

Purpose:
- track lineage between branched runs

Fields:
- `parent_run_id`: string or `null`
- `branched_from_chapter`: integer or `null`
- `branch_note`: string or empty string
- `branched_at`: ISO timestamp or `null`

V1 constraint:
- branch lineage is metadata only
- no merge-back mechanism is required in v1

### 9.2 Run Creation and Control

The app must support:
- create new run from worksheet path
- create new run from a file picker, not only manual path entry
- create new project from dossier inputs and convert it into a worksheet-backed run
- start cascade for one section
- auto-run remaining cascade sections
- run one chapter step
- auto-run all steps for a chapter
- resume after interruption using existing state files
- choose an output directory at run creation time or use a default

### 9.2.2 Loop Controls

The app must expose run controls beyond a simple start button.

Required controls:
- run once
- auto-run current chapter
- auto-run remaining cascade sections
- pause after current step
- cancel active job
- rerun a failed or completed step

Loop policy options for v1:
- continue automatically on success
- stop on validation failure
- stop on API error after retries
- optionally pause for human approval before advancing to the next step

### 9.2.3 Human Review Workflow

The app must support human-in-the-loop checkpoints.

For selected steps, the user must be able to choose one of:
- auto-advance
- require review before advancing
- require review only on warning or failure

At a review checkpoint, the user must be able to:
- approve and continue
- reject and rerun
- rerun with steering note
- edit the output manually and continue

### 9.2.3.1 Locked V1 Review Policy Defaults

To prevent hidden behavior differences between runs, v1 should ship with explicit step defaults.

Default review policy by step:
- `cascade`: `auto`
- `plan`: `manual`
- `draft`: `manual`
- `repetition`: `auto`
- `style`: `auto`
- `craft`: `auto`
- `final`: `manual`
- `summary`: `auto`

Interpretation:
- `auto`: advance immediately after successful validation
- `manual`: pause after step completion until user approves, reruns, or manually continues
- `on_warning`: pause only when warnings or failures occur

Rules:
- chapter auto-run must honor the configured review policy for each step
- a run-level override may replace the defaults
- the UI must show the effective policy before a loop starts

### 9.2.4 Steering Notes

The app must let the user attach a short run-scoped or step-scoped instruction when rerunning work.

Examples:
- "make chapter 3 darker"
- "reduce exposition"
- "keep Anna more guarded in internal narration"

V1 behavior:
- steering notes are stored in run metadata
- the backend appends them through a defined service-layer preamble rather than mutating base templates directly
- the prompt preview must show when a steering note is active

### 9.2.5 Run Branching

The app must support branching a run into a new run id for experimentation.

Use cases:
- test a different model config
- test revised templates
- test alternative chapter steering
- compare multiple finals before committing

Requirements:
- branch creation must copy the current run state
- branch metadata must record parent run id
- the UI must make source and branch lineage visible

### 9.2.6 Output Directory Behavior

The product must support a user-selectable output directory for generated artifacts.

V1 behavior:
- user may choose an output directory during run creation
- if omitted, the app uses the existing default under [`yfd-runner/output`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/output)
- manuscript generation writes to the selected output directory for that run

Optional extension if still in scope:
- separate advanced settings for `rendered/` prompt previews and manuscript output
- workspace-level default output directory in Settings

### 9.3 Live Progress

The app must show:
- job queued
- step started
- prompt rendered
- API call attempt number
- warning emitted
- step completed
- validation failed
- job aborted

At minimum, the live feed must identify:
- run id
- chapter
- step
- status
- timestamp
- short message

### 9.4 Prompt Preview

For templates, the app must let the user choose:
- run id
- chapter number or cascade section
- step name

Then render the exact prompt using the existing renderer logic and display:
- rendered markdown/text
- token estimate
- missing-variable errors if present

### 9.5 Metrics and Diagnostics

The app must surface:
- per-call metrics from run state
- cumulative metrics from [`yfd-runner/stats/cumulative.json`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/stats/cumulative.json)
- validation failure files under [`yfd-runner/rendered`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/rendered)

### 9.6 Search and Retrieval

The app should support full-text search across:
- worksheets
- plans
- drafts
- edit reports
- finals
- summaries

V1 minimum:
- search within a single run
- search results link directly to the relevant chapter and step

### 9.7 Comparison and Approval

The app must support comparison and explicit choice between candidate outputs.

V1 minimum:
- compare two outputs for the same chapter and step
- display prompt metadata differences
- allow the user to mark one output as preferred

---

## 10. API Surface

This is a preliminary API proposal, not a locked contract.

### Read endpoints

- `GET /api/runs`
- `GET /api/runs/{runId}`
- `GET /api/runs/{runId}/chapters/{chapter}`
- `GET /api/templates`
- `GET /api/templates/{name}`
- `GET /api/models`
- `GET /api/models/{name}`
- `GET /api/config`
- `GET /api/render/step`
- `GET /api/render/cascade`
- `GET /api/jobs/{jobId}`
- `GET /api/jobs/{jobId}/events`

### Write endpoints

- `POST /api/runs`
- `POST /api/projects/from-dossier`
- `POST /api/runs/{runId}/branch`
- `POST /api/runs/{runId}/cascade/{sectionNumber}`
- `POST /api/runs/{runId}/cascade/auto`
- `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}`
- `POST /api/runs/{runId}/chapters/{chapter}/auto`
- `POST /api/runs/{runId}/build-manuscript`
- `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/approve`
- `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/rerun`
- `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/manual-continue`
- `PUT /api/templates/{name}`
- `PUT /api/models/{name}`
- `PUT /api/config`
- `PUT /api/runs/{runId}/worksheet/{sectionKey}`

### Event stream

`GET /api/jobs/{jobId}/events`

Uses SSE and emits events such as:
- `job_started`
- `step_started`
- `attempt_started`
- `warning`
- `step_succeeded`
- `step_failed`
- `job_finished`

### 10.1 Locked V1 Endpoint Contracts

The following contracts are the first endpoints that should be treated as implementation targets rather than placeholders.

#### `POST /api/runs`

Purpose:
- create a run directly from a worksheet file

Request body:

```json
{
  "run_id": "eaw_001",
  "worksheet_path": "/abs/path/to/worksheet.md",
  "model_config": "default",
  "output_dir": "/abs/path/to/output",
  "review_policy": {
    "plan": "manual",
    "draft": "manual",
    "style": "auto",
    "craft": "auto",
    "final": "manual",
    "summary": "auto"
  }
}
```

Behavior:
- validate worksheet structure before creation
- reject H1 headings
- initialize run through the existing runner-compatible flow
- persist `studio.run_settings`

Success response:

```json
{
  "run_id": "eaw_001",
  "status": "created",
  "worksheet_validation": {
    "ok": true,
    "errors": []
  }
}
```

Error response:

```json
{
  "status": "validation_error",
  "errors": [
    {
      "code": "worksheet_h1_detected",
      "message": "Worksheet contains H1 headings. Top-level sections must use H2 (`##`)."
    }
  ]
}
```

#### `POST /api/projects/from-dossier`

Purpose:
- create a project intake session and initial worksheet draft from dossier inputs

Request body:

```json
{
  "run_id": "eaw_001",
  "blocks": [
    {
      "label": "brain_dump",
      "source_type": "pasted_text",
      "source_name": "session-input",
      "text": "Raw story concept..."
    },
    {
      "label": "character_notes",
      "source_type": "uploaded_markdown",
      "source_name": "anna-notes.md",
      "text": "Anna notes..."
    }
  ],
  "model_config": "default",
  "output_dir": "/abs/path/to/output"
}
```

Success response:

```json
{
  "run_id": "eaw_001",
  "status": "draft_ready",
  "dossier_blocks": [
    {
      "block_id": "blk_001",
      "label": "brain_dump",
      "mapping_targets": ["section_1.required_data_layer"]
    }
  ],
  "worksheet_draft": "## section_1_required_data_layer\n..."
}
```

V1 note:
- this endpoint may initially use rule-based normalization plus light backend heuristics
- it does not need DOCX/PDF parsing in v1

Error response:

```json
{
  "status": "validation_error",
  "errors": [
    {
      "code": "empty_dossier",
      "message": "At least one non-empty dossier block is required."
    }
  ]
}
```

#### `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/rerun`

Purpose:
- rerun a step with optional steering note and create a candidate output

Request body:

```json
{
  "steering_note": "Reduce exposition and keep the scene sharper.",
  "force": true,
  "review_mode": "manual"
}
```

Success response:

```json
{
  "job_id": "job_123",
  "status": "queued",
  "candidate_target": {
    "chapter": 3,
    "step": "draft"
  }
}
```

Behavior:
- enqueue a background job
- preserve the current canonical output until approval
- store the rerun output as a `studio.candidate_outputs` entry

Error cases:
- invalid step name
- run not found
- chapter not found when rerunning a post-plan step
- active job conflict for the same run

#### `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/approve`

Purpose:
- promote a candidate output into the canonical runner-compatible chapter field

Request body:

```json
{
  "candidate_id": "cand_123"
}
```

Success response:

```json
{
  "run_id": "eaw_001",
  "chapter": 3,
  "step": "draft",
  "approved_candidate_id": "cand_123",
  "status": "approved"
}
```

Behavior:
- write approved content into the canonical step slot
- mark review status as approved
- leave rejected or non-selected candidates intact for inspection

Validation rules:
- `candidate_id` must belong to the same run, chapter, and step
- only one candidate may be promoted at a time
- approval clears the pending review gate for that step

#### `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/manual-continue`

Purpose:
- accept user-edited text as the canonical output for a step and continue the loop

Request body:

```json
{
  "content": "User-edited final step output...",
  "review_note": "Tightened the opening and removed repetition."
}
```

Success response:

```json
{
  "run_id": "eaw_001",
  "chapter": 3,
  "step": "draft",
  "status": "saved"
}
```

Behavior:
- save the provided content into the canonical step slot
- create a `manual_edit` candidate record for traceability
- clear any pending review gate for that step

#### `GET /api/jobs/{jobId}/events`

Minimum SSE event payload:

```json
{
  "job_id": "job_123",
  "run_id": "eaw_001",
  "chapter": 3,
  "step": "draft",
  "event": "step_started",
  "message": "Draft step started",
  "timestamp": "2026-03-24T18:00:00Z"
}
```

### 10.2 API Behavior Rules

These rules apply across the locked v1 endpoints.

- write endpoints must return structured validation errors, not plain strings
- background-executed actions must return a `job_id`
- synchronous mutation endpoints may return final state directly
- all step names must use canonical internal names
- all file-path inputs must be absolute paths on the local machine
- no endpoint may silently overwrite canonical step output without either direct user intent or approval flow

---

## 11. Backend Design Notes

### 11.1 Direct module reuse vs shelling out

Preferred approach:
- import and call runner/state/renderer/api functions directly

Avoid as the default:
- spawning `python runner.py ...` subprocesses for every action

Reason:
- direct imports give better error handling
- easier progress events
- fewer quoting/path issues
- easier preview and validation APIs

### 11.2 Job execution

Long-running run actions should execute in background workers in the FastAPI process for v1.

Requirements:
- one active job per run by default
- clear job cancellation behavior
- no concurrent writes to the same run state
- event emission on every significant state transition

### 11.2.1 Backend additions needed beyond the current CLI

The current runner already accepts a worksheet path when initializing a run, but the web product will need additional service-layer behavior:
- worksheet validation endpoint before run creation
- explicit rejection of H1 headings in worksheet imports
- persisted per-run output directory setting
- service wrappers that pass custom output directories into manuscript and render functions
- dossier intake and normalization service
- steering-note injection layer
- review-state and approval tracking
- run-branch creation helpers

### 11.4 Backend Implementation Checklist

This section maps the first implementation pass onto the current Python modules.

#### Service layer

- create a thin service module that wraps runner operations for web use
- keep HTTP handlers free of business logic
- centralize path validation, review policy handling, and candidate promotion

#### `state.py` integration

- preserve existing run shape
- add support for a top-level `studio` key
- add helpers for reading and writing `studio.review_state`
- add helpers for reading and writing `studio.candidate_outputs`
- add helpers for branch metadata

#### `validator.py` additions

- add worksheet import validation for H1 rejection
- add reusable validation result objects for API responses
- avoid mixing terminal-facing messages with structured API validation

#### `renderer.py` integration

- keep renderer as the source of truth for prompt construction
- add a service-layer preamble path for steering notes without editing base templates
- expose preview-friendly wrappers for step and cascade render requests

#### `runner.py` and execution orchestration

- reuse chapter and cascade execution logic where possible
- separate interactive CLI prompts from web-safe execution paths
- ensure force/overwrite behavior is explicit in the service layer

#### `manuscript.py` integration

- pass per-run `output_dir` from `studio.run_settings`
- keep the default output directory behavior for runs that omit it

#### Job manager

- enforce one active job per run
- emit SSE events on queue, start, warning, completion, and failure
- persist enough metadata to recover UI state after a backend restart if feasible

### 11.3 File write safety

All write paths should use atomic temp-file replacement, matching the pattern already used in the runner where possible.

---

## 12. Frontend Design Notes

### Visual direction

The UI should feel like an intentional writing tool, not a generic admin panel.

Characteristics:
- editorial rather than enterprise
- dense where useful, but calm
- strong typographic hierarchy
- restrained motion
- obvious status colors for running, warning, failed, and complete states

### Editor requirements

- monospaced editor for templates and YAML
- markdown-friendly preview for rendered prompts and outputs
- split-pane editing on desktop
- stacked view on mobile or narrow widths

### Intake UX requirements

- imported material should be easy to review in chunks
- source-to-worksheet mapping should be visible, not hidden
- ambiguous mappings should be surfaced for user confirmation
- the user should always be able to inspect the raw imported source

### Run dashboard requirements

- chapter grid should make progress legible at a glance
- hover or click should reveal per-step details
- active job should always be visible globally

---

## 13. Suggested v1 Scope

### 13.0 Locked V1 Slice

The first usable release must stay narrow enough to build cleanly.

Locked v1 includes:
- create run from worksheet file
- create project from pasted/uploaded `.md` or `.txt` dossier material
- worksheet validation including H1 rejection
- template editor with prompt preview
- model editor
- run dashboard
- chapter auto-run and single-step run
- live job stream
- output inspector
- manual review for `plan`, `draft`, and `final`
- rerun with steering note
- custom manuscript output directory

Locked out of v1 even if desirable:
- DOCX/PDF dossier import
- branch promotion or merge semantics
- full search across all runs
- git-backed history UI
- advanced analytics
- compare more than two candidates at once

Rationale:
- this gives the user a complete prompt sequencer loop without forcing the first release to solve every authoring and experiment-management problem

### Must ship

- read/write templates
- read/write model configs
- create run
- create project from dossier or loose notes
- run one step
- run one full chapter
- run cascade auto
- live job progress
- output inspector
- prompt preview
- review and rerun controls
- worksheet validation with H1 rejection
- custom output directory for manuscript artifacts

### Should ship if still on schedule

- worksheet section editor
- config editor for `config.yaml`
- manuscript build trigger
- failure artifact viewer
- run branching
- comparison view
- run search

### Explicitly defer

- auth
- multi-user presence
- remote execution
- git history UI
- rich analytics dashboards
- DOCX/PDF dossier import
- branch merge/promotion semantics beyond metadata
- cross-run global search

---

## 14. Suggested Delivery Phases

### Phase 1: Backend wrapper

- add FastAPI service
- expose read APIs for runs, templates, models, and rendering
- expose write APIs for templates and models
- expose step execution endpoints
- add worksheet validation service
- add dossier intake service

### Phase 2: Core app shell

- add Next.js app
- implement navigation and run dashboard
- implement create-project wizard
- implement template editor
- implement model editor

### Phase 3: Live execution UX

- add SSE job stream
- show active step and status changes live
- add output inspector
- add review and rerun flow

### Phase 4: Refinement

- add worksheet editing
- add config editor
- add manuscript actions
- add run branching and comparison
- improve visual design and usability

---

## 15. Risks

### State mutation conflicts

The runner writes JSON files directly. Concurrent web actions could corrupt expectations unless the backend serializes writes per run.

### Long request handling

Step execution is not HTTP-request-shaped work. It must be job-based, not a blocking request/response pattern from the browser's perspective.

### Import boundary issues

The current runner modules are written for CLI use, not as a service layer. Some refactoring may be needed to separate pure logic from terminal-facing behavior.

### Local filesystem trust

The app edits live files. Validation and guarded writes are mandatory to avoid breaking templates or model YAML through a bad save.

### Spec drift vs current runner behavior

The current runner does not explicitly reject H1 headings in worksheet imports, and the CLI does not expose custom output directories even though some underlying functions accept them. The web app will therefore require modest backend additions rather than a pure thin wrapper.

### Intake ambiguity

Story dossiers and loose notes will often be incomplete, contradictory, or poorly structured. The intake flow must therefore support user confirmation and correction rather than pretending extraction is deterministic.

### Review-state complexity

Once approval gates, reruns, and branching exist, the product needs a clear concept of canonical output vs candidate output. This should be explicit in the service layer and UI state model.

---

## 16. Open Questions

- Should the backend wrap `runner.execute_step` directly, or introduce a new service layer around it first?
- Should `config.yaml` be edited as raw YAML only, or also through a structured form UI?
- Do we want template versioning inside the app in v1, or rely on git outside the app?
- Should rendered prompt previews be read-only, or support ad hoc edits before manual execution?
- Should the app expose raw state JSON anywhere, or keep all views structured?
- Do we want a local desktop packaging target later, such as Tauri or Electron, or stay browser-plus-local-server only?
- What is the minimal internal schema for imported dossier blocks before worksheet generation?
- Should review checkpoints be configurable per step globally, per run, or both?
- Do we store rejected and rerun candidate outputs in the same run file or as separate artifacts?
- What is the promotion model when a branch is preferred over its parent?

Resolved in this draft:
- v1 review defaults are explicit by step
- dossier mapping targets are intentionally narrow in v1
- candidate outputs remain non-canonical until approval

---

## 17. Initial Recommendation

Build the first version as:
- `FastAPI` backend in a new `server/` or `web-api/` directory
- `Next.js` frontend in a new `web/` directory
- direct integration with the current `yfd-runner` Python modules
- filesystem-backed persistence, no database in v1

This is the shortest path to a polished product without undermining the runner that already works.

---

## 18. Definition of Done for the First Usable Release

The first release is successful when a user can:
- open the app locally
- pick a worksheet file from the UI and get immediate structural validation
- create a project from story dossier inputs without touching the terminal
- edit a template and preview the rendered prompt
- edit a model config safely
- create or open a run
- choose or confirm an output directory for manuscript artifacts
- launch a chapter auto-run
- watch step progress live
- approve, reject, rerun, or manually continue a step from the UI
- inspect the saved draft, style report, craft report, final chapter, and summary
- recover from an interrupted run without touching the terminal

---

## 19. Appendix: Current Filesystem Areas the UI Must Understand

- [`yfd-runner/templates`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/templates)
- [`yfd-runner/models`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/models)
- [`yfd-runner/state`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/state)
- [`yfd-runner/rendered`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/rendered)
- [`yfd-runner/output`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/output)
- [`yfd-runner/stats`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/stats)
- [`yfd-runner/config.yaml`](/Users/carlo/claude-cowork-ghost-draft-npe/yfd-runner/config.yaml)
