from __future__ import annotations

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
    return state_dir, config_path, worksheet_path


def _create_temp_run(run_id: str, worksheet_path: Path) -> None:
    runner_bridge.runner_state.initialize_run(run_id, str(worksheet_path), model_config="default")


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
