from __future__ import annotations

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query

from . import runner_bridge

app = FastAPI(title="YFD Studio API", version="0.1.0")


class FileUpdateRequest(BaseModel):
    content: str


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
