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

### 11.2.1 Backend additions beyond the current CLI

The current runner already accepts a worksheet path when initializing a run. The web product adds service-layer behavior for:
- worksheet validation endpoint before run creation
- explicit rejection of H1 headings in worksheet imports
- persisted per-run output directory setting
- service wrappers that pass custom output directories into manuscript and render functions
- dossier intake and normalization service
- structured step-settings service over `step_models` and `step_overrides`
- steering-note injection layer
- review-state and approval tracking
- run-branch creation helpers

### 11.4 Backend Implementation Checklist

This section maps the first implementation pass onto the current Python modules.

#### Service layer

- create a thin service module that wraps runner operations for web use
- keep HTTP handlers free of business logic
- centralize path validation, review policy handling, and candidate promotion
- centralize structured step-settings reads and writes over `config.yaml`

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
- support cooperative cancellation at loop boundaries
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

## 13. Current Implementation Status

The app has moved beyond the original phased delivery outline. The current local implementation already includes:

- FastAPI service layer in `server/`
- Next.js frontend in `web/`
- run creation from worksheet input
- dossier intake from pasted or uploaded text/markdown blocks
- worksheet validation including H1 rejection
- template editing with prompt preview
- model editing
- structured step settings editing
- raw `config.yaml` editing
- run dashboard and run detail review surface
- run branching
- single-step execution, chapter auto-run, cascade execution, and manuscript build
- review, rerun, manual continue, and cooperative job cancellation
- worksheet section editing
- output inspector with artifact browsing and canonical-vs-candidate comparison
- single-run retrieval/search

Intentionally simplified parts of the current implementation:

- the job stream is SSE-compatible over in-memory job records rather than a full persisted event bus
- the frontend uses lightweight polling and route refresh behavior rather than a browser-side SSE client
- the frontend can render fallback read data when the backend is unavailable
- dossier mapping is intentionally narrow and does not yet expose a rich interactive mapping editor

## 14. Current Scope and Known Gaps

Shipped core v1 surfaces:

- runs
- intake
- templates
- models
- worksheets
- outputs
- settings
- config editor

Still intentionally deferred:

- DOCX/PDF dossier import
- branch promotion or merge semantics
- cross-run global search
- git-backed history UI
- remote execution
- auth and multi-user collaboration
- rich analytics dashboards
- comparison of more than two candidates at once

Recommended near-term work:

- improve browser-side live updates beyond route refresh and 2-second polling
- deepen dossier mapping and review controls before worksheet generation
- strengthen comparison ergonomics for branches and candidate outputs
- tighten documentation and testing around fallback mode versus live backend mode

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

The runner and the web app are intentionally close, but they are not identical surfaces. The web layer adds worksheet validation, run-scoped output directory handling, review metadata, and artifact browsing that do not exist as first-class CLI affordances.

### Intake ambiguity

Story dossiers and loose notes will often be incomplete, contradictory, or poorly structured. The intake flow must therefore support user confirmation and correction rather than pretending extraction is deterministic.

### Review-state complexity

Once approval gates, reruns, and branching exist, the product needs a clear concept of canonical output vs candidate output. This should be explicit in the service layer and UI state model.

---

## 16. Open Questions

Resolved in implementation:
- The backend uses a service layer around runner modules rather than calling CLI entrypoints directly from HTTP handlers.
- Review checkpoints are configurable per run through `studio.run_settings.review_policy`, with explicit locked defaults.
- Rejected and rerun candidate outputs live in the same run file under `studio.candidate_outputs`.
- V1 cancellation is cooperative at loop boundaries rather than mid-call interruption.

Still open:
- Do we want template versioning inside the app in v1, or rely on git outside the app?
- Should rendered prompt previews be read-only, or support ad hoc edits before manual execution?
- Should the app expose raw state JSON anywhere, or keep all views structured?
- Do we want a local desktop packaging target later, such as Tauri or Electron, or stay browser-plus-local-server only?
- What is the promotion model when a branch is preferred over its parent?

Resolved in this draft:
- v1 review defaults are explicit by step
- dossier mapping targets are intentionally narrow in v1
- candidate outputs remain non-canonical until approval

---

## 17. Current Recommendation

Keep the current shape:
- `FastAPI` backend in `server/`
- `Next.js` frontend in `web/`
- direct integration with the existing `yfd-runner` modules
- filesystem-backed persistence, no database in v1

The main priority is now refinement and documentation clarity rather than another architectural shift.

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

Most of this definition is already met in the local build. The remaining work is mostly refinement, deeper intake ergonomics, and more polished live-update behavior.

---

## 19. Appendix: Current Filesystem Areas the UI Must Understand

- [`yfd-runner/templates`](../yfd-runner/templates)
- [`yfd-runner/models`](../yfd-runner/models)
- [`yfd-runner/state`](../yfd-runner/state)
- [`yfd-runner/rendered`](../yfd-runner/rendered)
- [`yfd-runner/output`](../yfd-runner/output)
- [`yfd-runner/stats`](../yfd-runner/stats)
- [`yfd-runner/config.yaml`](../yfd-runner/config.yaml)
