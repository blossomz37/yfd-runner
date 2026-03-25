# YFD Studio — Product Spec, Part 2: Functional Requirements and API

**Part:** 2 of 3  
**Contains:** Sections 9-10  
**Previous:** [Part 1: Foundations and UX](./SPEC.md)  
**Next:** [Part 3: Implementation, Scope, and Delivery](./SPEC-implementation.md)

---

## 9. Functional Requirements

### 9.1 File Editing

The app must support direct editing of:
- template files under `templates/`
- model YAML files under `models/`
- config file [`yfd-runner/config.yaml`](../yfd-runner/config.yaml)
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
- if omitted, the app uses the existing default under [`yfd-runner/output`](../yfd-runner/output)
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
- cumulative metrics from [`yfd-runner/stats/cumulative.json`](../yfd-runner/stats/cumulative.json)
- validation failure files under [`yfd-runner/rendered`](../yfd-runner/rendered)

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
