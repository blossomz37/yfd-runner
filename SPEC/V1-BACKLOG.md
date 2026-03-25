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
  - `PUT /api/runs/{runId}/worksheet/{sectionKey}`
  - `POST /api/runs`
  - `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/approve`
  - `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/manual-continue`
- added worksheet validation with H1 rejection and structured validation errors
- added candidate approval and manual-edit traceability through `studio.review_state` and `studio.candidate_outputs`

## In Progress

### Backend wrapper

- stabilize the review and orchestration layer before frontend work
- preserve runner-compatible canonical state while adding `studio` metadata
- keep background job and live streaming work deferred until the contract settles

## Next

### Backend orchestration

- `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/rerun`
- `POST /api/runs/{runId}/chapters/{chapter}/auto`
- `POST /api/runs/{runId}/build-manuscript`
- per-run output directory wrappers for render/manuscript tasks
- active-job registry and conflict protection

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

- SSE job stream
- chapter execution matrix
- review gate UI
- rerun with steering note
- validation failure recovery screen
