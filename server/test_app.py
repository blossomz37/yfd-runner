from __future__ import annotations

import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from server.app import app
from server import runner_bridge


client = TestClient(app)


def _configure_temp_runner(tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path]:
    state_dir = tmp_path / "state"
    config_path = tmp_path / "config.yaml"
    worksheet_path = tmp_path / "worksheet.md"

    config_path.write_text(
        (
            "project:\n"
            "  name: test-project\n"
            "  total_chapters: 6\n"
            "openrouter:\n"
            "  base_url: https://openrouter.ai/api/v1/chat/completions\n"
        ),
        encoding="utf-8",
    )
    worksheet_path.write_text(
        (
            "## section_1_required_data_layer\n\n"
            "### required_data_layer\n"
            "**brain_dump:** test\n\n"
            "## section_2_story_concept\n\n"
            "[placeholder]\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(runner_bridge.runner_state, "STATE_DIR", state_dir)
    monkeypatch.setattr(runner_bridge.runner_state, "CONFIG_PATH", config_path)
    monkeypatch.setattr(runner_bridge.runner_manuscript, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(runner_bridge.runner_renderer, "RENDERED_DIR", tmp_path / "rendered")
    with runner_bridge.JOBS_LOCK:
        runner_bridge.JOBS.clear()
        runner_bridge.ACTIVE_RUN_JOBS.clear()
    return state_dir, config_path, worksheet_path


def _create_temp_run(run_id: str, worksheet_path: Path) -> None:
    runner_bridge.runner_state.initialize_run(run_id, str(worksheet_path), model_config="default")


def _wait_for_job(job_id: str, timeout_seconds: float = 3.0) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"succeeded", "failed", "cancelled"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Job did not finish in time: {job_id}")


def test_get_config() -> None:
    response = client.get("/api/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["path"] == "yfd-runner/config.yaml"
    assert payload["data"]["project"]["name"] == "eaw"


def test_get_model() -> None:
    response = client.get("/api/models/default.yaml")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "default.yaml"
    assert payload["data"]["model"] == "openai/gpt-5.4"


def test_put_template_rejects_invalid_jinja() -> None:
    response = client.put(
        "/api/templates/01-plan.j2",
        json={"content": "{% if broken %}"},
    )
    assert response.status_code == 400
    assert "Template validation failed" in response.json()["detail"]


def test_put_model_rejects_missing_model_field() -> None:
    response = client.put(
        "/api/models/default.yaml",
        json={"content": "temperature: 0.5\n"},
    )
    assert response.status_code == 400
    assert "model" in response.json()["detail"]


def test_put_config_rejects_non_mapping_yaml() -> None:
    response = client.put(
        "/api/config",
        json={"content": "- not\n- a\n- mapping\n"},
    )
    assert response.status_code == 400
    assert "mapping" in response.json()["detail"]


def test_validate_worksheet_rejects_h1_heading(tmp_path: Path) -> None:
    worksheet = tmp_path / "bad.md"
    worksheet.write_text("# bad heading\n", encoding="utf-8")

    response = client.post(
        "/api/validate/worksheet",
        json={"worksheet_path": str(worksheet)},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert any(error["code"] == "worksheet_h1_detected" for error in payload["errors"])


def test_create_run_creates_state_file(tmp_path: Path, monkeypatch) -> None:
    state_dir, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)

    response = client.post(
        "/api/runs",
        json={
            "run_id": "api_created",
            "worksheet_path": str(worksheet_path),
            "model_config": "default",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "created"
    assert payload["worksheet_validation"]["ok"] is True
    assert (state_dir / "api_created.json").exists()


def test_put_worksheet_section_updates_run_state(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("editable_run", worksheet_path)

    response = client.put(
        "/api/runs/editable_run/worksheet/section_2_story_concept",
        json={"content": "Refined premise text.\n\n- stronger conflict"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "saved"
    assert payload["worksheet_validation"]["ok"] is True

    updated = runner_bridge.runner_state.load_state("editable_run")
    assert "## section_2_story_concept" in updated["worksheet"]
    assert "Refined premise text." in updated["worksheet"]


def test_manual_continue_saves_canonical_output_and_candidate(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("review_run", worksheet_path)

    response = client.post(
        "/api/runs/review_run/chapters/1/steps/draft/manual-continue",
        json={
            "content": "Draft rewrite ready for continuation.",
            "review_note": "Tightened the opening.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "saved"

    updated = runner_bridge.runner_state.load_state("review_run")
    assert updated["chapters"]["1"]["draft"] == "Draft rewrite ready for continuation."
    candidate = updated["studio"]["candidate_outputs"][0]
    assert candidate["candidate_id"] == payload["candidate_id"]
    assert candidate["source"] == "manual_edit"
    assert candidate["status"] == "approved"
    review_state = updated["studio"]["review_state"]["1"]["draft"]
    assert review_state["approved_candidate_id"] == payload["candidate_id"]
    assert review_state["review_status"] == "approved"
    assert review_state["review_required"] is False


def test_approve_candidate_promotes_content_into_canonical_step(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("approval_run", worksheet_path)

    def seed_review_state(data: dict) -> None:
        data.setdefault("chapters", {}).setdefault("3", {})["draft"] = "Original draft"
        data["studio"] = {
            "review_state": {
                "3": {
                    "draft": {
                        "review_required": True,
                        "review_reason": "policy",
                        "review_status": "pending",
                        "approved_candidate_id": None,
                        "last_reviewed_at": None,
                    }
                }
            },
            "candidate_outputs": [
                {
                    "candidate_id": "cand_old",
                    "chapter": 3,
                    "step": "draft",
                    "source": "rerun",
                    "steering_note": "",
                    "content": "Stale candidate",
                    "status": "approved",
                    "created_at": runner_bridge.runner_state.now_iso(),
                },
                {
                    "candidate_id": "cand_123",
                    "chapter": 3,
                    "step": "draft",
                    "source": "rerun",
                    "steering_note": "Reduce exposition.",
                    "content": "Improved candidate draft",
                    "status": "candidate",
                    "created_at": runner_bridge.runner_state.now_iso(),
                },
            ],
        }

    runner_bridge.runner_state.update_state("approval_run", seed_review_state)

    response = client.post(
        "/api/runs/approval_run/chapters/3/steps/draft/approve",
        json={"candidate_id": "cand_123"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["approved_candidate_id"] == "cand_123"

    updated = runner_bridge.runner_state.load_state("approval_run")
    assert updated["chapters"]["3"]["draft"] == "Improved candidate draft"
    outputs = {candidate["candidate_id"]: candidate for candidate in updated["studio"]["candidate_outputs"]}
    assert outputs["cand_123"]["status"] == "approved"
    assert outputs["cand_old"]["status"] == "rejected"
    review_state = updated["studio"]["review_state"]["3"]["draft"]
    assert review_state["approved_candidate_id"] == "cand_123"
    assert review_state["review_status"] == "approved"
    assert review_state["review_required"] is False


def test_build_manuscript_job_uses_run_output_dir(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("manuscript_run", worksheet_path)
    output_dir = tmp_path / "custom-output"

    def seed_manuscript_state(data: dict) -> None:
        data.setdefault("chapters", {}).setdefault("1", {})["final"] = "Chapter one text."
        data.setdefault("chapters", {}).setdefault("2", {})["final"] = "Chapter two text."
        studio = data.setdefault("studio", {})
        studio["run_settings"] = {
            "output_dir": str(output_dir),
            "review_policy": {},
            "default_steering_note": "",
            "created_from": "worksheet",
        }

    runner_bridge.runner_state.update_state("manuscript_run", seed_manuscript_state)

    response = client.post("/api/runs/manuscript_run/build-manuscript")
    assert response.status_code == 200
    job = _wait_for_job(response.json()["job_id"])
    assert job["status"] == "succeeded"

    manuscript_path = output_dir / "manuscript_run_manuscript.md"
    assert manuscript_path.exists()
    assert "# Chapter 1" in manuscript_path.read_text(encoding="utf-8")
    assert job["result"]["output_path"] == str(manuscript_path)


def test_chapter_auto_run_job_executes_runner_step_order(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("auto_run", worksheet_path)
    calls: list[str] = []

    def fake_execute_step(run_id: str, chapter: int, step_name: str, model_config=None, force: bool = False) -> str:
        del model_config, force
        calls.append(step_name)
        storage_step = runner_bridge._storage_step_name(step_name)
        runner_bridge.runner_state.save_step_output(run_id, chapter, storage_step, f"{storage_step} output.")
        return f"{step_name} complete"

    monkeypatch.setattr(runner_bridge.runner_cli, "execute_step", fake_execute_step)

    response = client.post("/api/runs/auto_run/chapters/1/auto", json={"force": True})
    assert response.status_code == 200
    job = _wait_for_job(response.json()["job_id"])
    assert job["status"] == "succeeded"
    assert calls == ["plan"]
    assert job["result"]["completed_steps"] == ["plan"]
    assert job["result"]["paused_at"]["step"] == "plan"
    updated = runner_bridge.runner_state.load_state("auto_run")
    review_state = updated["studio"]["review_state"]["1"]["plan"]
    assert review_state["review_status"] == "pending"
    assert updated["studio"]["candidate_outputs"][0]["source"] == "initial_run"


def test_single_step_endpoint_sets_manual_review_checkpoint(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("single_step_run", worksheet_path)

    def seed_existing_chapter(data: dict) -> None:
        data.setdefault("chapters", {}).setdefault("1", {})["plan"] = "Existing plan."

    runner_bridge.runner_state.update_state("single_step_run", seed_existing_chapter)

    def fake_execute_step(run_id: str, chapter: int, step_name: str, model_config=None, force: bool = False) -> str:
        del model_config, force
        storage_step = runner_bridge._storage_step_name(step_name)
        runner_bridge.runner_state.save_step_output(run_id, chapter, storage_step, f"{storage_step} content")
        return f"{storage_step} content"

    monkeypatch.setattr(runner_bridge.runner_cli, "execute_step", fake_execute_step)

    response = client.post("/api/runs/single_step_run/chapters/1/steps/draft", json={})
    assert response.status_code == 200
    job = _wait_for_job(response.json()["job_id"])
    assert job["status"] == "succeeded"
    assert job["result"]["review_required"] is True

    updated = runner_bridge.runner_state.load_state("single_step_run")
    assert updated["chapters"]["1"]["draft"] == "draft content"
    assert updated["studio"]["review_state"]["1"]["draft"]["review_status"] == "pending"
    assert updated["studio"]["candidate_outputs"][0]["source"] == "initial_run"


def test_rerun_job_creates_candidate_without_overwriting_canonical_output(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("rerun_run", worksheet_path)

    def seed_rerun_state(data: dict) -> None:
        data.setdefault("chapters", {}).setdefault("2", {})["draft"] = "Canonical draft stays."
        studio = data.setdefault("studio", {})
        studio["run_settings"] = {
            "output_dir": None,
            "review_policy": {"draft": "manual"},
            "default_steering_note": "",
            "created_from": "worksheet",
        }

    runner_bridge.runner_state.update_state("rerun_run", seed_rerun_state)

    monkeypatch.setattr(
        runner_bridge.runner_api,
        "call_step",
        lambda *args, **kwargs: {
            "response": {
                "choices": [
                    {
                        "message": {
                            "content": ("Candidate rewrite with enough complete words to satisfy validation. " * 90).strip()
                            + "."
                        }
                    }
                ],
                "usage": {},
            },
            "model_config": {"model": "mock/model"},
            "attempts": 1,
        },
    )
    monkeypatch.setattr(runner_bridge.runner_metrics, "update_cumulative", lambda *args, **kwargs: {})

    response = client.post(
        "/api/runs/rerun_run/chapters/2/steps/draft/rerun",
        json={"steering_note": "Sharpen the scene.", "review_mode": "manual"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"

    job = _wait_for_job(payload["job_id"])
    assert job["status"] == "succeeded"

    updated = runner_bridge.runner_state.load_state("rerun_run")
    assert updated["chapters"]["2"]["draft"] == "Canonical draft stays."
    candidate = updated["studio"]["candidate_outputs"][0]
    assert candidate["candidate_id"] == job["result"]["candidate_id"]
    assert candidate["source"] == "rerun"
    assert candidate["status"] == "candidate"
    assert candidate["steering_note"] == "Sharpen the scene."
    review_state = updated["studio"]["review_state"]["2"]["draft"]
    assert review_state["review_status"] == "pending"
    assert review_state["review_required"] is True


def test_job_events_endpoint_streams_sse_payload(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("events_run", worksheet_path)

    def fake_execute_step(run_id: str, chapter: int, step_name: str, model_config=None, force: bool = False) -> str:
        del model_config, force
        storage_step = runner_bridge._storage_step_name(step_name)
        runner_bridge.runner_state.save_step_output(run_id, chapter, storage_step, "plan content")
        return "plan content"

    monkeypatch.setattr(runner_bridge.runner_cli, "execute_step", fake_execute_step)

    response = client.post("/api/runs/events_run/chapters/1/steps/plan", json={})
    job = _wait_for_job(response.json()["job_id"])
    assert job["status"] == "succeeded"

    stream_response = client.get(f"/api/jobs/{response.json()['job_id']}/events")
    assert stream_response.status_code == 200
    assert stream_response.headers["content-type"].startswith("text/event-stream")
    assert "event: job_queued" in stream_response.text
    assert "event: job_finished" in stream_response.text


def test_run_cascade_section_updates_worksheet(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("cascade_run", worksheet_path)

    monkeypatch.setattr(
        runner_bridge.runner_api,
        "call_step",
        lambda *args, **kwargs: {
            "response": {"choices": [{"message": {"content": "## section_2_story_concept\n\nResolved section content."}}], "usage": {}},
            "model_config": {"model": "mock/model"},
            "attempts": 1,
        },
    )
    monkeypatch.setattr(runner_bridge.runner_metrics, "update_cumulative", lambda *args, **kwargs: {})

    response = client.post("/api/runs/cascade_run/cascade/2", json={})
    assert response.status_code == 200
    job = _wait_for_job(response.json()["job_id"])
    assert job["status"] == "succeeded"

    updated = runner_bridge.runner_state.load_state("cascade_run")
    assert "Resolved section content." in updated["worksheet"]


def test_run_cascade_auto_completes_remaining_sections(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("cascade_auto_run", worksheet_path)

    def seed_incomplete_cascade_section(data: dict) -> None:
        data["worksheet"] = (
            "## section_1_required_data_layer\n\n"
            "### required_data_layer\n"
            "**brain_dump:** test\n\n"
            "## section_2_story_concept\n\n"
            "[PLACEHOLDER SECTION CONTENT THAT SHOULD REMAIN INCOMPLETE]\n"
        )

    runner_bridge.runner_state.update_state("cascade_auto_run", seed_incomplete_cascade_section)

    monkeypatch.setattr(
        runner_bridge.runner_api,
        "call_step",
        lambda *args, **kwargs: {
            "response": {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "## section_2_story_concept\n\n"
                                "Auto cascade content with enough detail to satisfy the minimum response length."
                            )
                        }
                    }
                ],
                "usage": {},
            },
            "model_config": {"model": "mock/model"},
            "attempts": 1,
        },
    )
    monkeypatch.setattr(runner_bridge.runner_metrics, "update_cumulative", lambda *args, **kwargs: {})

    response = client.post("/api/runs/cascade_auto_run/cascade/auto", json={})
    assert response.status_code == 200
    job = _wait_for_job(response.json()["job_id"])
    assert job["status"] == "succeeded"
    assert job["result"]["completed_sections"][0]["section_number"] == 2


def test_active_job_conflict_blocks_second_run_scoped_job(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("conflict_run", worksheet_path)
    entered = threading.Event()
    release = threading.Event()
    blocked = {"value": False}

    def slow_execute_step(run_id: str, chapter: int, step_name: str, model_config=None, force: bool = False) -> str:
        del run_id, chapter, step_name, model_config, force
        if not blocked["value"]:
            blocked["value"] = True
            entered.set()
            release.wait(2.0)
        return "ok"

    monkeypatch.setattr(runner_bridge.runner_cli, "execute_step", slow_execute_step)

    first_response = client.post("/api/runs/conflict_run/chapters/1/auto", json={})
    assert first_response.status_code == 200
    assert entered.wait(1.0)

    second_response = client.post("/api/runs/conflict_run/build-manuscript")
    assert second_response.status_code == 409
    assert second_response.json()["status"] == "active_job_conflict"

    release.set()
    job = _wait_for_job(first_response.json()["job_id"])
    assert job["status"] == "succeeded"


def test_cancel_running_chapter_auto_job_stops_before_next_step(tmp_path: Path, monkeypatch) -> None:
    _, _, worksheet_path = _configure_temp_runner(tmp_path, monkeypatch)
    _create_temp_run("cancel_run", worksheet_path)

    def seed_auto_policies(data: dict) -> None:
        studio = data.setdefault("studio", {})
        studio["run_settings"] = {
            "output_dir": None,
            "review_policy": {
                "plan": "auto",
                "draft": "auto",
                "repetition_audit": "auto",
                "style": "auto",
                "craft": "auto",
                "final": "auto",
                "summary": "auto",
            },
            "default_steering_note": "",
            "created_from": "worksheet",
        }

    runner_bridge.runner_state.update_state("cancel_run", seed_auto_policies)

    entered = threading.Event()
    release = threading.Event()
    calls: list[str] = []

    def slow_execute_step(run_id: str, chapter: int, step_name: str, model_config=None, force: bool = False) -> str:
        del model_config, force
        calls.append(step_name)
        storage_step = runner_bridge._storage_step_name(step_name)
        runner_bridge.runner_state.save_step_output(run_id, chapter, storage_step, f"{storage_step} output")
        if step_name == "plan":
            entered.set()
            release.wait(2.0)
        return f"{storage_step} output"

    monkeypatch.setattr(runner_bridge.runner_cli, "execute_step", slow_execute_step)

    response = client.post("/api/runs/cancel_run/chapters/2/auto", json={})
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert entered.wait(1.0)

    cancel_response = client.post(f"/api/jobs/{job_id}/cancel")
    assert cancel_response.status_code == 200
    cancel_payload = cancel_response.json()
    assert cancel_payload["cancel_requested"] is True

    release.set()
    job = _wait_for_job(job_id)
    assert job["status"] == "cancelled"
    assert calls == ["plan"]
    assert job["error"] == "Job cancelled before starting the next unit of work"

    stream_response = client.get(f"/api/jobs/{job_id}/events")
    assert stream_response.status_code == 200
    assert "event: cancel_requested" in stream_response.text
    assert "event: job_cancelled" in stream_response.text
