# YFD Studio — Spec Evaluation

**Evaluator notes — March 25, 2026**

---

## Overall Assessment

This is an unusually well-structured product spec for a solo/small-team project. The three-part split (foundations → requirements → implementation) is clean. The writing is precise and avoids the common spec failure mode of describing vibes instead of behavior. The locked V1 slice is clearly scoped, the API contracts include request/response shapes with error cases, and the internal data model (`studio.*` keys) is defined before anyone writes UI code against it.

That said, there are structural gaps, some scope risks, and a few places where the spec is either silent or contradicts the existing codebase. What follows is organized by severity.

---

## Strengths

**Grounded in the existing system.** The spec repeatedly defers to `yfd-runner` as the execution engine and source of truth. It doesn't reinvent the workflow — it wraps it. The `runner_bridge.py` implementation reflects this faithfully: direct imports from runner modules, no subprocess shelling, and atomic file writes matching the runner's own pattern.

**Locked defaults for review policy.** Specifying which steps default to `manual` vs `auto` review (Section 9.2.3.1) prevents a class of ambiguity bugs. The implementation already honors these defaults correctly.

**Candidate output model is sound.** The distinction between canonical runner state (`chapters["3"]["draft"]`) and `studio.candidate_outputs` is the right architectural choice. It means the CLI runner never sees uncommitted web-app state, and reruns don't silently overwrite working content.

**Dossier intake scope is intentionally narrow.** The locked V1 target taxonomy (Section 9.1.3.1) avoids the trap of pretending AI extraction is reliable. The explicit "rules-based normalization plus light heuristics" note is honest.

**Backend implementation is well ahead of the spec's delivery phases.** The backlog shows all read and write endpoints implemented, including the review/approval flow, SSE event streaming, and run-scoped job conflict protection. That's Phases 1–3 of the delivery plan largely complete on the backend side.

---

## Issues: Things the Spec Gets Wrong or Leaves Unresolved

### 1. No multi-chapter auto-run — spec doesn't address this

The runner only handles one chapter at a time (`--chapter N --auto`). The spec defines `POST /api/runs/{runId}/chapters/{chapter}/auto` (single chapter) but never discusses a "run remaining chapters" operation. For a 25-chapter novel, this means the user must manually trigger each chapter from the UI — 25 separate actions. The cascade has `--auto` for all remaining sections; the chapter loop needs an equivalent.

**Recommendation:** Add a `POST /api/runs/{runId}/auto` endpoint that loops from the current chapter through the total, respecting review gates. The `queue_chapter_auto_run` worker pattern already exists and could be wrapped in an outer loop.

### 2. The `from-dossier` endpoint has no implementation

`POST /api/projects/from-dossier` is specified with full request/response contracts (Section 10.1), listed in the locked V1 slice, but is absent from both `app.py` and `runner_bridge.py`. The `Intake Workspace` screen (Section 8.5.1) depends on it.

**Recommendation:** Either implement the endpoint or explicitly move it to the "next" column in V1-BACKLOG.md. Right now the spec and backlog disagree about what's shipped.

### 3. Run branching has no implementation

`POST /api/runs/{runId}/branch` is in the API surface and the `studio.branch` data model is defined, but there's no implementation in the bridge. The spec lists branching as "should ship if still on schedule" but the V1 slice includes "rerun with steering note" and comparison view — both of which lose significant value without branching.

**Recommendation:** Clarify whether branching is V1 or not. If yes, it's a straightforward state-copy operation and should be quick to implement. If no, remove it from the API surface and data model to avoid spec drift.

### 4. Search is underspecified

Section 9.6 says "full-text search across worksheets, plans, drafts, edit reports, finals, summaries" with "V1 minimum: search within a single run." There's no API endpoint for this, no implementation, and no UI screen. Since the data lives in flat JSON state files, search would either mean scanning every field in a run's JSON, or building a lightweight index.

**Recommendation:** Either define a `GET /api/runs/{runId}/search?q=...` endpoint and add it to the backlog, or move search entirely to "explicitly defer."

### 5. Cancellation is cooperative-only *(updated)*

Section 9.2.2 lists "cancel active job" as a required control. A `POST /api/jobs/{jobId}/cancel` endpoint and cooperative cancellation at loop boundaries (between steps and between cascade sections) have been added. However, cancellation cannot interrupt a mid-flight API call — the runner's `api.call_step` has no interruption hook. The current behavior is: the job is marked cancelled, and the loop stops at the next boundary.

**Recommendation:** This is the right V1 trade-off. True mid-call interruption can be deferred. The spec and backlog should note the cooperative-only semantics explicitly.

### 6. SSE implementation is polling-based, not event-driven

`iter_job_events` polls the job record every 50ms in a busy loop. This works at single-user scale but will burn CPU if multiple jobs or clients are connected. The spec says "SSE endpoint for progress streaming" — the current implementation is closer to "SSE-shaped polling."

**Recommendation:** This is fine for V1 but should be flagged as a known limitation. A `threading.Condition` or `asyncio.Queue` would be the clean fix.

### 7. Step settings (token limits, temperature, model assignment) need a dedicated UI surface

The spec (Section 9.1) says the app must support editing `config.yaml`, and the implementation supports this via `PUT /api/config`. But `config.yaml` is where the most operationally critical settings live — `step_models` (which model runs each step) and `step_overrides` (per-step `max_tokens`, `temperature`, and other parameters). The current API treats the entire config as a raw YAML blob. Users should never have to manually edit source files to change these settings.

The runner base code does not need to change. `api.resolve_model_config()` already reads `step_models` and `step_overrides` as plain dictionary lookups from the loaded config at call time (lines 87–99 of `api.py`). It doesn't care how those values were written.

What's needed is in the server layer only:

- A `GET /api/step-settings` endpoint that returns the merged view of `step_models` + `step_overrides` as structured JSON per step (model name, max_tokens, temperature, plus any extras like `reasoning.effort`).
- A `PUT /api/step-settings/{step}` endpoint that accepts structured fields and writes them back into the correct spots in `config.yaml`.
- A frontend Step Settings panel that surfaces per-step model assignment, max_tokens, and temperature in one structured form — not a raw YAML editor.

This is a V1 requirement, not a nice-to-have. During this evaluation session, the `max_tokens` ceiling for all steps had to be manually bumped from 8,000 to 60,000 to prevent `incomplete_ending` validation failures. A user without terminal fluency (the spec's stated audience) would have no way to diagnose or fix this without a dedicated settings surface.

**Recommendation:** Add the structured step-settings endpoints to the API surface and backlog. The frontend panel should show effective values per step, and ideally warn when values are unusually low or exceed known model context limits.

### 8. The `force` flag semantics differ between CLI and API

In the CLI, `--force` both skips overwrite prompts AND bypasses validation. In the API, the `StepRunRequest.force` field is passed through to `runner_cli.execute_step`, which calls `maybe_prompt_overwrite` — but that function reads from `input()` when not forced, which would hang in a web context. The bridge avoids this by always passing `force=True` through to execution, but the spec doesn't acknowledge this behavioral difference.

**Recommendation:** Document that the web API always operates in force mode for overwrites (since the UI handles confirmation via the review flow), and that validation bypass is separate.

---

## Issues: Spec Organization and Clarity

### 9. Open questions that are already answered by implementation

Section 16 lists ten open questions. Several are already resolved by the existing code:

- "Should the backend wrap `runner.execute_step` directly, or introduce a new service layer?" → Answered: service layer (`runner_bridge.py`).
- "Should review checkpoints be configurable per step globally, per run, or both?" → Answered: per-run via `studio.run_settings.review_policy`, with global defaults.
- "Do we store rejected and rerun candidate outputs in the same run file or as separate artifacts?" → Answered: same run file under `studio.candidate_outputs`.

**Recommendation:** Update Section 16 to mark resolved questions and move them to a "Resolved" subsection (some already are, but several more should be).

### 10. Mockup brief references screens the spec doesn't fully define

The `SPEC-CSS-MOCKUPS-v2.md` brief references four screens (Runs Dashboard, Run Detail, Template Editor, Validation Failure Recovery). The spec defines these conceptually in Section 8 but the mockup brief adds specifics (command palette, review rail, failure recovery actions) that should be promoted into the main spec. Right now the mockup doc is carrying requirements that aren't tracked in the spec proper.

**Recommendation:** Fold the mockup-specific requirements (command palette, explicit action sets, visual hierarchy priorities) into Section 8 or a new Section 8.8.

---

## Scope Risks for V1

**The intake flow is the biggest scope risk.** Dossier import, normalization, mapping, and user confirmation (Sections 9.1.2–9.1.3.1) is a substantial feature with AI-assisted extraction, user-editable mappings, and a multi-step wizard. If the primary use case is "I already have a worksheet," this can be deferred entirely without blocking core value. If it's "I have loose notes and want the pipeline to help me start," it's essential but will eat significant frontend time.

**The comparison view is the second risk.** Side-by-side diff of two outputs with metadata comparison (Section 8.7) requires a diff rendering component, candidate selection UI, and promotion logic. The backend pieces exist (candidate outputs, approval), but the frontend work is non-trivial.

**Recommendation:** Ship V1 with the worksheet-creation path and single-candidate review flow. Dossier intake and comparison view can follow as V1.1 without breaking the architecture.

---

## What's in Good Shape and Ready to Build Against

The following areas are well-specified enough to start frontend implementation immediately:

- Runs Dashboard (Section 8.1) — all data available via `GET /api/runs`
- Run Detail / Chapter Grid (Section 8.2) — all data available via `GET /api/runs/{runId}`
- Template Editor + Preview (Section 8.3) — read/write/preview endpoints all working
- Model Editor (Section 8.4) — read/write endpoints working
- Output Inspector (Section 8.6) — step output available in run state, review/rerun/approve endpoints working
- Live Job Progress (Section 9.3) — SSE events streaming from job log
- Create Run (Section 8.1.1) — endpoint with worksheet validation working
- Chapter Auto-Run (Section 9.2.2) — endpoint with review-policy pause working

---

## Summary

The spec is strong. The backend is substantially ahead of the frontend. The main risks are scope creep from intake and comparison features, and a few gaps where the spec describes behavior that isn't implemented (dossier, branching, search, cancellation). The architecture is sound and the data model choices are good. The next high-value move is standing up the frontend shell and wiring it to the endpoints that already exist.
