"""Exercise the actual route and saved reports with a fake provider only."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import APIStatusError, APITimeoutError

from app.main import app
from app.services import run_reports
from week2.exercise.run_cases import collect_predictions
from week2.exercise import run_cases as collector
from week2.exercise import run_eval
from week2.exercise.run_eval import new_report, write_reports


@pytest.fixture
def demo(tmp_path, monkeypatch):
    output = {"summary": "Nira will update checkout tests.", "decisions": [],
              "actions": [{"owner": "Nira", "action": "Update checkout tests", "due_date": None}]}
    cases = [{"id": name, "title": f"Invented meeting {name}",
              "input": f"Meeting {name}: Nira will update checkout tests.", "expected": output} for name in ["D1", "D2"]]
    source = tmp_path / "dataset.json"
    source.write_text(json.dumps(cases), encoding="utf-8")
    monkeypatch.setattr(run_reports, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(run_reports, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(run_reports, "DATASETS", {"original": {"label": "Two invented cases", "path": source}})
    provider = MagicMock()
    provider.__enter__.return_value = provider
    provider.responses.create.return_value = SimpleNamespace(
        status="completed", id="fake-response", model="offline-fake-model", usage=None,
        output_text=json.dumps(output), output=[],
    )
    monkeypatch.setattr("app.main.create_client", lambda: provider)
    with TestClient(app) as api:
        yield api, provider, cases


def test_single_case_collector_uses_real_route_and_server_saves_metadata(demo):
    api, provider, cases = demo
    started = api.post("/demo/runs", json={"dataset": "original", "case_id": "D2"})
    assert started.status_code == 201
    run = started.json()
    assert run["case_ids"] == ["D2"] and "expected" not in run["cases"][0]
    collect_predictions(api, run["cases"], run)
    saved = run_reports.read_run(run["run_id"])
    assert saved["transport"] == "http" and saved["endpoint"] == "/analyze-meeting"
    assert len(saved["predictions"]) == 1
    prediction = saved["predictions"][0]
    assert prediction["case_id"] == "D2" and prediction["http_status"] == 200
    assert prediction["status"] == "ok" and prediction["model"] == "offline-fake-model"
    assert prediction["raw_output"] == provider.responses.create.return_value.output_text
    messages = provider.responses.create.call_args.kwargs["input"]
    assert messages == [{"role": "developer", "content": saved["prompt"]},
                        {"role": "user", "content": cases[1]["input"]}]
    provider.responses.create.assert_called_once()
    results = api.get(f"/demo/runs/{run['run_id']}").json()
    assert results["summary"] is None and results["comparisons"] == []
    assert api.get(f"/demo/runs/{run['run_id']}/files/predictions.json").status_code == 200
    assert api.get(f"/demo/runs/{run['run_id']}/files/.env").status_code == 404


def test_all_case_run_and_unchanged_evaluator_results_are_visible(demo):
    api, provider, cases = demo
    started = api.post("/demo/runs", json={"dataset": "original"}).json()
    collect_predictions(api, started["cases"], started)
    saved = run_reports.read_run(started["run_id"])
    assert len(saved["predictions"]) == 2 and provider.responses.create.call_count == 2
    folder = run_reports.run_directory(started["run_id"])
    report = new_report(saved, (folder / "predictions.json").read_bytes(),
                        (run_reports.PROJECT_ROOT / "dataset.json").read_bytes(), "Invented evaluator instructions.")
    report["judgments"] = [{"case_id": case["id"], "status": "ok", "judgment": {
        "decision_matches": [], "action_matches": [{"expected_index": 0, "predicted_index": 0, "reason": "Same task."}],
        "summary_supported": True, "summary_complete": True, "notes": "Synthetic judgment, no model call.",
    }} for case in cases]
    write_reports(folder, cases, saved, report)
    results = api.get(f"/demo/runs/{started['run_id']}").json()
    assert results["summary"]["f1"] == "100.00%" and results["summary"]["meetings"] == "2"
    assert {row["case_id"] for row in results["comparisons"]} == {"D1", "D2"}
    assert api.get("/demo/runs").json()[0]["evaluated"] is True


@pytest.mark.parametrize("kind,expected_status,saved_status", [
    ("timeout", 504, "api_error"), ("server", 502, "api_error"),
    ("malformed", 502, "invalid_output"), ("incomplete", 502, "response_error"),
])
def test_failed_live_route_saves_controlled_error(demo, kind, expected_status, saved_status):
    api, provider, cases = demo
    run = api.post("/demo/runs", json={"case_id": "D1"}).json()
    request = httpx.Request("POST", "https://example.invalid")
    if kind == "timeout":
        provider.responses.create.side_effect = APITimeoutError(request=request)
    elif kind == "server":
        provider.responses.create.side_effect = APIStatusError("dummy-secret", response=httpx.Response(500, request=request), body=None)
    elif kind == "malformed":
        provider.responses.create.return_value.output_text = "not JSON"
    else:
        provider.responses.create.return_value.status = "incomplete"
    result = api.post("/analyze-meeting", json={"meeting_text": cases[0]["input"]},
                      headers={"X-Run-ID": run["run_id"], "X-Case-ID": "D1"})
    assert result.status_code == expected_status
    saved = run_reports.read_run(run["run_id"])["predictions"][0]
    assert saved["status"] == saved_status and saved["http_status"] == expected_status
    assert "dummy-secret" not in json.dumps(saved) + result.text


def test_custom_input_uses_normal_route_without_creating_a_run(demo):
    api, provider, _ = demo
    result = api.post("/analyze-meeting", json={"hello": "Invented notes."})
    assert result.status_code == 422
    assert result.json()["errors"] == ["meeting_text is required.", "Remove unexpected field: hello."]
    provider.responses.create.assert_not_called()
    assert api.post("/analyze-meeting", json={"meeting_text": "Custom invented notes."}).status_code == 200
    provider.responses.create.assert_called_once()
    assert not run_reports.REPORTS_DIR.exists()


def test_invalid_run_context_never_reaches_provider(demo):
    api, provider, cases = demo
    run = api.post("/demo/runs", json={"case_id": "D1"}).json()
    headers = {"X-Run-ID": run["run_id"], "X-Case-ID": "D1"}
    assert api.post("/analyze-meeting", json={"meeting_text": "Different source."}, headers=headers).status_code == 409
    assert api.post("/analyze-meeting", json={"meeting_text": cases[0]["input"]},
                    headers={"X-Run-ID": run["run_id"]}).status_code == 400
    assert api.post("/demo/runs", json={"case_id": "UNKNOWN"}).status_code == 400
    provider.responses.create.assert_not_called()


def test_configuration_datasets_and_cors_are_safe_to_view(demo):
    api, provider, _ = demo
    config = api.get("/demo/config").json()
    assert set(config) == {"model", "settings", "prompt", "schema", "versions"}
    assert "api_key" not in config
    assert api.get("/demo/datasets").json()[0]["count"] == 2
    assert all("expected" not in case for case in api.get("/demo/datasets/original").json())
    result = api.options("/analyze-meeting", headers={"Origin": "http://127.0.0.1:5500",
                        "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "X-Run-ID,X-Case-ID"})
    assert result.status_code == 200 and result.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5500"
    provider.responses.create.assert_not_called()


def test_terminal_collector_creates_run_through_api_and_calls_same_route(demo, monkeypatch):
    api, provider, _ = demo
    wrapper = MagicMock()
    wrapper.__enter__.return_value = api
    factory = MagicMock(return_value=wrapper)
    monkeypatch.setattr(collector.httpx, "Client", factory)
    monkeypatch.setattr("sys.argv", ["run_cases", "--live", "--case-id", "D1"])
    collector.main()
    provider.responses.create.assert_called_once()
    runs = api.get("/demo/runs").json()
    assert len(runs) == 1 and runs[0]["selected"] == runs[0]["completed"] == 1
    factory.assert_called_once_with(base_url=collector.API_URL, timeout=None, trust_env=False)


@pytest.fixture
def judge_client(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    judgment = {"decision_matches": [], "action_matches": [
        {"expected_index": 0, "predicted_index": 0, "reason": "Same task."}],
        "summary_supported": True, "summary_complete": True, "notes": "Offline test judgment."}
    client.responses.create.return_value = SimpleNamespace(
        status="completed", id="fake-judge", model="offline-fake-model", usage=None,
        output_text=json.dumps(judgment), output=[],
    )
    monkeypatch.setattr(run_eval, "create_client", lambda: client)
    return client


def test_evaluation_route_writes_reports_and_terminal_reuses_same_cache(demo, judge_client):
    api, _, cases = demo
    run = api.post("/demo/runs", json={"case_id": "D1"}).json()
    collect_predictions(api, run["cases"], run)
    response = api.post(f"/demo/runs/{run['run_id']}/evaluate")
    assert response.status_code == 200
    results = response.json()
    assert results["summary"]["f1"] == "100.00%"
    assert set(results["files"]) == {"predictions.json", "judge_results.json", "eval.csv", "summary.csv"}
    request = judge_client.responses.create.call_args.kwargs
    assert json.loads(request["input"][1]["content"])["expected"] == cases[0]["expected"]
    assert api.post(f"/demo/runs/{run['run_id']}/evaluate").status_code == 200
    summary = run_eval.evaluate_run(run_reports.run_directory(run["run_id"]))
    assert summary["f1"] == 1.0
    judge_client.responses.create.assert_called_once()


def test_evaluation_route_keeps_failed_judgments_visible_and_resumes_only_failed(demo, judge_client):
    api, _, _ = demo
    run = api.post("/demo/runs", json={}).json()
    collect_predictions(api, run["cases"], run)
    good_response = judge_client.responses.create.return_value
    judge_client.responses.create.side_effect = [good_response, APITimeoutError(request=httpx.Request("POST", "https://example.invalid"))]
    result = api.post(f"/demo/runs/{run['run_id']}/evaluate").json()
    assert result["summary"]["status"] == "incomplete"
    assert result["summary"]["f1"] == "" and result["summary"]["judge_errors"] == "1"
    judge_client.responses.create.side_effect = None
    result = api.post(f"/demo/runs/{run['run_id']}/evaluate").json()
    assert result["summary"]["f1"] == "100.00%"
    assert judge_client.responses.create.call_count == 3


def test_evaluation_route_rejects_missing_and_stale_runs_before_judging(demo, judge_client):
    api, _, _ = demo
    assert api.post("/demo/runs/missing/evaluate").status_code == 404
    run = api.post("/demo/runs", json={"case_id": "D1"}).json()
    collect_predictions(api, run["cases"], run)
    folder = run_reports.run_directory(run["run_id"])
    predictions_before = (folder / "predictions.json").read_bytes()
    assert api.post(f"/demo/runs/{run['run_id']}/evaluate").status_code == 200
    saved = json.loads((folder / "judge_results.json").read_text(encoding="utf-8"))
    saved["metadata"]["judge"]["prompt"] = "Changed instructions."
    (folder / "judge_results.json").write_text(json.dumps(saved), encoding="utf-8")
    judge_client.responses.create.reset_mock()
    assert api.post(f"/demo/runs/{run['run_id']}/evaluate").status_code == 409
    judge_client.responses.create.assert_not_called()
    assert (folder / "predictions.json").read_bytes() == predictions_before
