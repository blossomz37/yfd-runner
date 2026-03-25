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

## In Progress

### Backend wrapper

- scaffold `server/`
- expose read-only endpoints for:
  - `GET /healthz`
  - `GET /api/runs`
  - `GET /api/runs/{runId}`
  - `GET /api/templates`
  - `GET /api/templates/{name}`
  - `GET /api/models`
  - `GET /api/render/step`

## Next

### Backend write-safe endpoints

- `PUT /api/templates/{name}`
- `PUT /api/models/{name}`
- `GET /api/config`
- worksheet validation service

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
