# YFD Studio — Current State

Last updated: 2026-03-25

## Shipped Backend Surface

Read endpoints:

- `GET /healthz`
- `GET /api/runs`
- `GET /api/runs/{runId}`
- `GET /api/runs/{runId}/artifacts`
- `GET /api/runs/{runId}/manuscript`
- `GET /api/runs/{runId}/artifacts/content`
- `GET /api/templates`
- `GET /api/templates/{name}`
- `GET /api/models`
- `GET /api/models/{name}`
- `GET /api/config`
- `GET /api/step-settings`
- `GET /api/render/step`
- `GET /api/render/cascade`
- `GET /api/jobs/{jobId}`
- `GET /api/jobs/{jobId}/events`

Write endpoints:

- `POST /api/validate/worksheet`
- `POST /api/runs`
- `POST /api/projects/from-dossier`
- `POST /api/runs/{runId}/branch`
- `POST /api/runs/{runId}/build-manuscript`
- `POST /api/runs/{runId}/chapters/{chapter}/auto`
- `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}`
- `POST /api/runs/{runId}/cascade/auto`
- `POST /api/runs/{runId}/cascade/{sectionNumber}`
- `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/rerun`
- `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/approve`
- `POST /api/runs/{runId}/chapters/{chapter}/steps/{step}/manual-continue`
- `POST /api/jobs/{jobId}/cancel`
- `PUT /api/templates/{name}`
- `PUT /api/models/{name}`
- `PUT /api/config`
- `PUT /api/step-settings/{step}`
- `PUT /api/runs/{runId}/worksheet/{sectionKey}`

Implementation notes:

- Job execution is serialized per run.
- Cancellation is cooperative at loop boundaries.
- Job events are stored in memory and exposed through snapshot polling plus an SSE-compatible endpoint.
- Web-specific run metadata lives under `studio` in the run state file.

## Shipped Frontend Surface

Routes:

- `/` runs dashboard
- `/intake` worksheet and dossier intake
- `/templates` template editor and preview
- `/models` model editor
- `/worksheets` run-scoped worksheet explorer and section editor
- `/outputs` run-scoped outputs inspector
- `/settings` structured step settings
- `/config` advanced raw config editor
- `/runs/[runId]` run detail, review, execution controls, and single-run retrieval

Current run detail capabilities:

- approve, rerun with steering note, and manual continue
- branch creation
- single-step execution
- chapter auto-run
- cascade run-once and auto-run
- manuscript build trigger
- active job panel with 2-second polling

## Known Intentional Gaps

- no browser-side SSE client yet; live updates rely on polling and route refreshes
- no DOCX or PDF dossier intake
- no branch merge or promotion semantics
- no cross-run global search
- no git-backed history UI
- no auth or multi-user support
- no remote execution mode

## Current Behavioral Differences From Ideal Target

- The frontend can render fallback read data when the backend is offline. This is for shell validation only; writes still require the backend.
- The dossier intake flow preserves and stores blocks, but the UI for manual target remapping is still shallow.
- The output inspector is run-scoped first. Cross-run comparison is deferred.

## Next Recommended Work

1. Improve live-update behavior beyond polling on the run detail page.
2. Deepen dossier mapping and pre-worksheet review controls.
3. Improve branch and candidate comparison ergonomics.
4. Expand documentation and test coverage around fallback mode and live-backend mode.
