"""Use fake model responses/errors, just like Week 1. No network calls."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAIError, RateLimitError

from app.main import app, get_client
from app.schemas import MeetingAnalysis
from app.services import llm


def sample_output() -> dict:
    return {
        "summary": "Nira will update the checkout tests; no deadline was set.",
        "decisions": [],
        "actions": [{"owner": "Nira", "action": "Update checkout tests", "due_date": None}],
    }


@pytest.fixture
def fake_client():
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(
        status="completed", output_text=json.dumps(sample_output()), output=[],
    )
    app.dependency_overrides[get_client] = lambda: client
    yield client
    app.dependency_overrides.clear()


def test_success_returns_validated_json_and_requests_structured_output(fake_client):
    meeting_text = "Nira will update the checkout tests. No deadline was set."
    with TestClient(app) as api:
        result = api.post("/analyze-meeting", json={"meeting_text": meeting_text})
    assert result.status_code == 200
    assert result.json() == sample_output()
    MeetingAnalysis.model_validate(result.json())
    request = fake_client.responses.create.call_args.kwargs
    assert request["input"][1] == {"role": "user", "content": meeting_text}
    assert request["input"][0]["role"] == "developer"
    assert request["text"]["format"] == {
        "type": "json_schema", "name": "meeting_analysis",
        "schema": MeetingAnalysis.model_json_schema(), "strict": True,
    }
    assert request["model"] == llm.MODEL
    assert request["store"] is False


@pytest.mark.parametrize("payload,errors", [
    ({}, ["meeting_text is required."]),
    ({"meeting_text": " "}, ["meeting_text must contain text, not just spaces."]),
    ({"meeting_text": ""}, ["meeting_text must contain text, not just spaces."]),
    ({"meeting_text": 123}, ["meeting_text must be text."]),
    ({"meeting_text": None}, ["meeting_text must be text."]),
    ({"hello": "M"}, ["meeting_text is required.", "Remove unexpected field: hello."]),
    ([], ["Request body must be a JSON object."]),
])
def test_invalid_payload_returns_422_without_model_request(fake_client, payload, errors):
    with TestClient(app) as api:
        result = api.post("/analyze-meeting", json=payload)
    assert result.status_code == 422
    assert result.json() == {"detail": "Invalid request body.", "errors": errors}
    fake_client.responses.create.assert_not_called()


def test_malformed_json_returns_readable_error_without_echoing_input(fake_client):
    with TestClient(app) as api:
        result = api.post("/analyze-meeting", content='{"meeting_text": "dummy-secret",}',
                          headers={"Content-Type": "application/json"})
    assert result.status_code == 422
    assert result.json() == {"detail": "Invalid request body.",
                             "errors": ["Send valid JSON, with field names and text in double quotes."]}
    assert "dummy-secret" not in result.text
    fake_client.responses.create.assert_not_called()


@pytest.mark.parametrize("kind, expected_status, expected_detail", [
    ("timeout", 504, "Model service timed out."),
    ("429", 503, "Model service is rate limited; try again later."),
    ("500", 502, "Model service request failed."),
    ("403", 502, "Model service rejected the request. Check the model and API key permissions."),
    ("connection", 502, "Model service request failed."),
])
def test_upstream_failure_becomes_safe_http_error(fake_client, kind, expected_status, expected_detail, caplog):
    request = httpx.Request("POST", "https://example.invalid/v1/responses")
    if kind == "timeout":
        error = APITimeoutError(request=request)
    elif kind == "connection":
        error = APIConnectionError(message="dummy-secret must not be logged", request=request)
    else:
        response = httpx.Response(int(kind), request=request)
        error_class = RateLimitError if kind == "429" else APIStatusError
        error = error_class("dummy-secret must not be logged", response=response, body=None)
    fake_client.responses.create.side_effect = error
    with TestClient(app) as api:
        result = api.post("/analyze-meeting", json={"meeting_text": "Synthetic notes"})
    assert result.status_code == expected_status
    assert result.json()["detail"] == expected_detail
    if kind in {"429", "500", "403"}:
        assert result.json()["upstream_status"] == int(kind)
    if kind == "timeout":
        assert result.json()["error_type"] == "timeout"
    assert "dummy-secret" not in result.text + caplog.text


@pytest.mark.parametrize("output", [
    "not JSON", "{}", '{"summary":"Text","decisions":[],"actions":"wrong type"}',
    json.dumps({"summary": "Text", "decisions": [], "actions": [
        {"owner": None, "action": "Update tests", "due_date": "2026-02-30"},
    ]}),
])
def test_malformed_model_response_returns_502(fake_client, output):
    fake_client.responses.create.return_value.output_text = output
    with TestClient(app) as api:
        result = api.post("/analyze-meeting", json={"meeting_text": "Synthetic notes"})
    assert result.status_code == 502
    assert result.json()["error_type"] == "invalid_output"


@pytest.mark.parametrize("status", ["incomplete", "failed"])
def test_incomplete_response_is_rejected_even_with_valid_json(fake_client, status):
    fake_client.responses.create.return_value.status = status
    with TestClient(app) as api:
        result = api.post("/analyze-meeting", json={"meeting_text": "Synthetic notes"})
    assert result.status_code == 502
    assert result.json()["error_type"] == "response_error"


def test_refusal_is_rejected_even_with_valid_json(fake_client):
    fake_client.responses.create.return_value.output = [SimpleNamespace(
        type="message", content=[SimpleNamespace(type="refusal")],
    )]
    with TestClient(app) as api:
        result = api.post("/analyze-meeting", json={"meeting_text": "Synthetic notes"})
    assert result.status_code == 502


def test_docs_and_openapi_are_available_without_model_client():
    with TestClient(app) as api:
        assert api.get("/docs").status_code == 200
        schema = api.get("/openapi.json").json()
    operation = schema["paths"]["/analyze-meeting"]["post"]
    assert "MeetingRequest" in str(operation["requestBody"])
    assert "MeetingAnalysis" in str(operation["responses"]["200"])
    assert operation["responses"]["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/InvalidRequest",
    }


def test_missing_configuration_returns_safe_503(monkeypatch):
    def missing_configuration():
        raise OpenAIError("dummy-secret must not be returned")
    monkeypatch.setattr("app.main.create_client", missing_configuration)
    with TestClient(app) as api:
        result = api.post("/analyze-meeting", json={"meeting_text": "Synthetic notes"})
    assert result.status_code == 503
    assert result.json() == {"detail": "Model service is not configured."}


def test_client_settings_are_explicit_without_opening_a_connection(monkeypatch):
    fake_openai = Mock()
    monkeypatch.setattr(llm, "OpenAI", fake_openai)
    monkeypatch.setattr(llm, "load_dotenv", Mock())
    assert llm.create_client() is fake_openai.return_value
    fake_openai.assert_called_once_with(timeout=30.0, max_retries=1)
