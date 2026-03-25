# YFD Studio — Product Spec, Part 3: Implementation, Scope, and Delivery

**Part:** 3 of 3  
**Contains:** Sections 11-19  
**Previous:** [Part 2: Functional Requirements and API](./SPEC-requirements.md)

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

- [`yfd-runner/templates`](../yfd-runner/templates)
- [`yfd-runner/models`](../yfd-runner/models)
- [`yfd-runner/state`](../yfd-runner/state)
- [`yfd-runner/rendered`](../yfd-runner/rendered)
- [`yfd-runner/output`](../yfd-runner/output)
- [`yfd-runner/stats`](../yfd-runner/stats)
- [`yfd-runner/config.yaml`](../yfd-runner/config.yaml)
