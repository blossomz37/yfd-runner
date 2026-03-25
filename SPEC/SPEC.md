# YFD Studio — Product Spec, Part 1: Foundations and UX

**Part:** 1 of 3  
**Contains:** Sections 1-8  
**Next:** [Part 2: Functional Requirements and API](./SPEC-requirements.md)

---

**Project:** Web application for authoring, running, and inspecting the YFD pipeline  
**Working name:** `YFD Studio`  
**Repository root:** `.`  
**Status:** Preliminary draft for iteration

---

## 1. Product Summary

YFD Studio is a polished local-first web app that sits on top of the existing `yfd-runner` Python pipeline.

It should let a user:
- edit prompt templates in [`yfd-runner/templates`](../yfd-runner/templates)
- edit model configs in [`yfd-runner/models`](../yfd-runner/models)
- inspect and edit run state in [`yfd-runner/state`](../yfd-runner/state)
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
- [`yfd-runner/runner.py`](../yfd-runner/runner.py): orchestration and CLI entry point
- [`yfd-runner/renderer.py`](../yfd-runner/renderer.py): Jinja rendering and step context assembly
- [`yfd-runner/api.py`](../yfd-runner/api.py): OpenRouter request execution
- [`yfd-runner/state.py`](../yfd-runner/state.py): run state persistence
- [`yfd-runner/metrics.py`](../yfd-runner/metrics.py): per-run and cumulative metrics
- [`yfd-runner/validator.py`](../yfd-runner/validator.py): output validation

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
- all known runs from [`yfd-runner/state`](../yfd-runner/state)
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
- records branch metadata only; merge and promotion semantics remain explicit follow-up actions
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
- list of files in [`yfd-runner/templates`](../yfd-runner/templates)
- syntax-highlighted editor
- template preview panel
- warnings for undefined variables or render errors

Actions:
- save
- render preview for selected run/chapter
- diff against last saved version in session

#### 8.4 Model Editor

Shows:
- list of YAML model configs in [`yfd-runner/models`](../yfd-runner/models)
- parsed form plus raw YAML mode
- structured step settings panel for per-step model assignment and step overrides
- effective settings after step overrides

Actions:
- save
- validate YAML
- compare model configs
- edit step model assignment, token ceiling, and temperature without touching raw YAML

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
- normalize input through rule-based cleanup and narrow mapping heuristics
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
