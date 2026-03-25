from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from . import runner_bridge

app = FastAPI(title="YFD Studio API", version="0.1.0")


class FileUpdateRequest(BaseModel):
    content: str


class WorksheetValidationRequest(BaseModel):
    worksheet_path: str


class WorksheetSectionUpdateRequest(BaseModel):
    content: str


class CreateRunRequest(BaseModel):
    run_id: str
    worksheet_path: str
    model_config_name: str | None = Field(default=None, alias="model_config")
    output_dir: str | None = None
    review_policy: dict[str, str] | None = None


class ChapterAutoRunRequest(BaseModel):
    model_config_name: str | None = Field(default=None, alias="model_config")
    force: bool = False


class StepRunRequest(BaseModel):
    model_config_name: str | None = Field(default=None, alias="model_config")
    force: bool = False


class CascadeRunRequest(BaseModel):
    model_config_name: str | None = Field(default=None, alias="model_config")
    force: bool = False


class StepApprovalRequest(BaseModel):
    candidate_id: str


class ManualContinueRequest(BaseModel):
    content: str
    review_note: str = ""


class StepRerunRequest(BaseModel):
    steering_note: str = ""
    force: bool = False
    review_mode: str = "manual"
    model_config_name: str | None = Field(default=None, alias="model_config")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/runs")
def get_runs() -> dict[str, object]:
    return {"runs": runner_bridge.list_runs()}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    try:
        return runner_bridge.get_run(run_id)
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/templates")
def get_templates() -> dict[str, object]:
    return {"templates": runner_bridge.list_templates()}


@app.get("/api/templates/{name}")
def get_template(name: str) -> dict[str, str]:
    try:
        return runner_bridge.get_template(name)
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/models")
def get_models() -> dict[str, object]:
    return {"models": runner_bridge.list_models()}


@app.get("/api/models/{name}")
def get_model(name: str) -> dict[str, object]:
    try:
        return runner_bridge.get_model(name)
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/config")
def get_config() -> dict[str, object]:
    return runner_bridge.get_config()


@app.put("/api/config")
def put_config(request: FileUpdateRequest) -> dict[str, object]:
    try:
        return runner_bridge.update_config(request.content)
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/validate/worksheet")
def validate_worksheet(request: WorksheetValidationRequest):
    try:
        return runner_bridge.validate_worksheet_path(request.worksheet_path)
    except runner_bridge.ValidationBridgeError as exc:
        return JSONResponse(status_code=400, content={"status": "validation_error", "errors": exc.errors})


@app.put("/api/templates/{name}")
def put_template(name: str, request: FileUpdateRequest) -> dict[str, object]:
    try:
        return runner_bridge.update_template(name, request.content)
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/models/{name}")
def put_model(name: str, request: FileUpdateRequest) -> dict[str, object]:
    try:
        return runner_bridge.update_model(name, request.content)
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/render/step")
def render_step(
    run_id: str = Query(...),
    chapter: int = Query(..., ge=1),
    step: str = Query(...),
) -> dict[str, object]:
    try:
        return runner_bridge.render_step_preview(run_id=run_id, chapter=chapter, step=step)
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/render/cascade")
def render_cascade(
    run_id: str = Query(...),
    section_number: int = Query(..., ge=1),
) -> dict[str, object]:
    try:
        return runner_bridge.render_cascade_preview(run_id=run_id, section_number=section_number)
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs")
def create_run(request: CreateRunRequest):
    try:
        return runner_bridge.create_run(
            run_id=request.run_id,
            worksheet_path=request.worksheet_path,
            model_config=request.model_config_name,
            output_dir=request.output_dir,
            review_policy=request.review_policy,
        )
    except runner_bridge.ValidationBridgeError as exc:
        return JSONResponse(status_code=400, content={"status": "validation_error", "errors": exc.errors})
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    try:
        return runner_bridge.get_job(job_id)
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/jobs/{job_id}/events")
def get_job_events(job_id: str):
    try:
        runner_bridge.get_job(job_id)
        stream = runner_bridge.iter_job_events(job_id)
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StreamingResponse(stream, media_type="text/event-stream")


@app.post("/api/runs/{run_id}/build-manuscript")
def build_manuscript(run_id: str) -> dict[str, object]:
    try:
        return runner_bridge.queue_build_manuscript(run_id)
    except runner_bridge.JobConflictBridgeError as exc:
        return JSONResponse(
            status_code=409,
            content={"status": "active_job_conflict", "run_id": exc.run_id, "active_job_id": exc.active_job_id},
        )
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/chapters/{chapter}/auto")
def auto_run_chapter(run_id: str, chapter: int, request: ChapterAutoRunRequest) -> dict[str, object]:
    try:
        return runner_bridge.queue_chapter_auto_run(
            run_id=run_id,
            chapter=chapter,
            model_config=request.model_config_name,
            force=request.force,
        )
    except runner_bridge.JobConflictBridgeError as exc:
        return JSONResponse(
            status_code=409,
            content={"status": "active_job_conflict", "run_id": exc.run_id, "active_job_id": exc.active_job_id},
        )
    except runner_bridge.ValidationBridgeError as exc:
        return JSONResponse(status_code=400, content={"status": "validation_error", "errors": exc.errors})
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/chapters/{chapter}/steps/{step}")
def run_single_step(run_id: str, chapter: int, step: str, request: StepRunRequest) -> dict[str, object]:
    try:
        return runner_bridge.queue_execute_step(
            run_id=run_id,
            chapter=chapter,
            step=step,
            model_config=request.model_config_name,
            force=request.force,
        )
    except runner_bridge.JobConflictBridgeError as exc:
        return JSONResponse(
            status_code=409,
            content={"status": "active_job_conflict", "run_id": exc.run_id, "active_job_id": exc.active_job_id},
        )
    except runner_bridge.ValidationBridgeError as exc:
        return JSONResponse(status_code=400, content={"status": "validation_error", "errors": exc.errors})
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/cascade/auto")
def run_cascade_auto(run_id: str, request: CascadeRunRequest) -> dict[str, object]:
    try:
        return runner_bridge.queue_cascade_auto(
            run_id=run_id,
            model_config=request.model_config_name,
            force=request.force,
        )
    except runner_bridge.JobConflictBridgeError as exc:
        return JSONResponse(
            status_code=409,
            content={"status": "active_job_conflict", "run_id": exc.run_id, "active_job_id": exc.active_job_id},
        )
    except runner_bridge.ValidationBridgeError as exc:
        return JSONResponse(status_code=400, content={"status": "validation_error", "errors": exc.errors})
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/cascade/{section_number}")
def run_cascade_section(run_id: str, section_number: int, request: CascadeRunRequest) -> dict[str, object]:
    try:
        return runner_bridge.queue_cascade_section(
            run_id=run_id,
            section_number=section_number,
            model_config=request.model_config_name,
            force=request.force,
        )
    except runner_bridge.JobConflictBridgeError as exc:
        return JSONResponse(
            status_code=409,
            content={"status": "active_job_conflict", "run_id": exc.run_id, "active_job_id": exc.active_job_id},
        )
    except runner_bridge.ValidationBridgeError as exc:
        return JSONResponse(status_code=400, content={"status": "validation_error", "errors": exc.errors})
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/chapters/{chapter}/steps/{step}/rerun")
def rerun_step(run_id: str, chapter: int, step: str, request: StepRerunRequest) -> dict[str, object]:
    try:
        return runner_bridge.queue_rerun_step(
            run_id=run_id,
            chapter=chapter,
            step=step,
            steering_note=request.steering_note,
            force=request.force,
            review_mode=request.review_mode,
            model_config=request.model_config_name,
        )
    except runner_bridge.JobConflictBridgeError as exc:
        return JSONResponse(
            status_code=409,
            content={"status": "active_job_conflict", "run_id": exc.run_id, "active_job_id": exc.active_job_id},
        )
    except runner_bridge.ValidationBridgeError as exc:
        return JSONResponse(status_code=400, content={"status": "validation_error", "errors": exc.errors})
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/runs/{run_id}/worksheet/{section_key}")
def put_worksheet_section(run_id: str, section_key: str, request: WorksheetSectionUpdateRequest):
    try:
        return runner_bridge.update_worksheet_section(run_id, section_key, request.content)
    except runner_bridge.ValidationBridgeError as exc:
        return JSONResponse(status_code=400, content={"status": "validation_error", "errors": exc.errors})
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/chapters/{chapter}/steps/{step}/approve")
def approve_step_candidate(run_id: str, chapter: int, step: str, request: StepApprovalRequest):
    try:
        return runner_bridge.approve_candidate(run_id, chapter, step, request.candidate_id)
    except runner_bridge.ValidationBridgeError as exc:
        return JSONResponse(status_code=400, content={"status": "validation_error", "errors": exc.errors})
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/chapters/{chapter}/steps/{step}/manual-continue")
def manual_continue_step(run_id: str, chapter: int, step: str, request: ManualContinueRequest):
    try:
        return runner_bridge.manual_continue(
            run_id=run_id,
            chapter=chapter,
            step=step,
            content=request.content,
            review_note=request.review_note,
        )
    except runner_bridge.ValidationBridgeError as exc:
        return JSONResponse(status_code=400, content={"status": "validation_error", "errors": exc.errors})
    except runner_bridge.BridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
