from __future__ import annotations

from fastapi.testclient import TestClient

from server.app import app


client = TestClient(app)


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
