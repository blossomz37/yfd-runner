# YFD Studio V1 Backlog

Purpose: turn the locked v1 slice into an implementation-facing checklist.

## Current Phase Order

1. Repo hygiene and setup
2. Backend wrapper
3. Core app shell
4. First vertical slice: runs plus template preview
5. Live execution and review flow

## Completed

- split product spec into three documents
- normalized spec and README links to workspace-relative paths
- added root `requirements.txt`
- ignored local `.venv/`
- pushed `main` to GitHub
- scaffolded `server/`
- exposed read-only endpoints for:
  - `GET /healthz`
  - `GET /api/runs`
  - `GET /api/runs/{runId}`
  - `GET /api/templates`
  - `GET /api/templates/{name}`
  - `GET /api/models`
  - `GET /api/models/{name}`
  - `GET /api/config`
  - `GET /api/render/step`
  - `GET /api/render/cascade`
- added write-safe endpoints for:
  - `PUT /api/templates/{name}`
  - `PUT /api/models/{name}`
  - `PUT /api/config`
  - `PUT /api/step-settings/{step}`
  - `PUT /api/runs/{runId}/worksheet/{sectionKey}`
  - `POST /api/runs`
  - `POST /api/projects/from-dossier`
  - `POST /api/runs/{runId}/branch`
  - `GET /api/jobs/{jobId}`
  - `GET /api/jobs/{jobId}/events`
  - `POST /api/runs/{runId}/build-manuscript`
  - `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}`
  - `POST /api/runs/{runId}/chapters/{chapter}/auto`
  - `POST /api/runs/{runId}/cascade/{sectionNumber}`
  - `POST /api/runs/{runId}/cascade/auto`
  - `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/rerun`
  - `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/approve`
  - `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/manual-continue`
- added worksheet validation with H1 rejection and structured validation errors
- added candidate approval and manual-edit traceability through `studio.review_state` and `studio.candidate_outputs`
- added dossier-backed run creation with `studio.dossier_blocks` persistence and worksheet draft synthesis
- added metadata-only run branching with `studio.branch` lineage
- added structured step settings over `step_models` and `step_overrides`
- added polling job records plus run-scoped active-job conflict protection
- added SSE-compatible job event streaming over the in-process job log
- added review-policy pause handling for single-step and chapter auto-run execution
- added queued cascade execution for single sections and auto-completion
- added cooperative job cancellation for queued jobs and between-step / between-section loop boundaries
- added prompt-rendered, attempt, warning, validation-failure, and step-failure events for step execution
- added rerun `on_warning` review handling without overwriting canonical outputs

## In Progress

### Backend wrapper

- preserve runner-compatible canonical state while adding `studio` metadata
- keep the in-process job/event contract stable before frontend work

### Backend orchestration

- keep execution mutations behind run-scoped conflict protection
- avoid overwriting canonical outputs during rerun flows
- keep step and cascade execution behavior aligned with the existing runner validation rules
- keep cancellation semantics explicit about cooperative stopping versus mid-call interruption
- keep event naming and payloads stable enough for the first frontend slice

## Next

### Frontend shell

- app shell with left nav and command surface
- runs dashboard
- template editor shell

### First vertical slice

- open app
- list runs
- open run detail
- preview a selected template against a run and chapter

### After the first slice

- chapter execution matrix
- review gate UI
- rerun with steering note
- validation failure recovery screen

### Optional backend follow-ups

- richer event payload details such as rendered template paths or token-budget metadata
- true push-based SSE delivery instead of polling the in-memory job log
