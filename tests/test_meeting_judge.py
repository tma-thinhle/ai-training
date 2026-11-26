"""Exercise the judge and saved-run CLI with fake SDK responses only."""

import hashlib
import csv
import json
import subprocess
import sys
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APIStatusError

from app.schemas import MeetingAnalysis
from app.services.llm import MODEL
from week2.exercise.evaluate import evaluate_predictions
from week2.exercise.run_cases import DATASET_PATH
from week2.exercise.run_eval import JUDGE_PROMPT_PATH, collect_judgments, new_report, write_reports


def sample_data():
    expected = {"summary": "Nira will update checkout tests.", "decisions": [],
                "actions": [{"owner": "Nira", "action": "Update checkout tests", "due_date": None}]}
    cases = [{"id": "EXAMPLE-A", "input": "Nira will update checkout tests.", "expected": expected}]
    run = {"model": MODEL, "prompt": "Extract only supported information.", "settings": {},
           "schema": MeetingAnalysis.model_json_schema(), "case_ids": ["EXAMPLE-A"],
           "predictions": [{"case_id": "EXAMPLE-A", "status": "ok", "analysis": expected}]}
    judgment = {"decision_matches": [], "action_matches": [
        {"expected_index": 0, "predicted_index": 0, "reason": "Same task."}],
        "summary_supported": True, "summary_complete": True, "notes": "Synthetic test judgment."}
    report = new_report(run, json.dumps(run).encode(), json.dumps(cases).encode(), "Dedicated evaluator rules.")
    response = SimpleNamespace(status="completed", id="mock-judge", model="mock-model", usage=None,
                               output_text=json.dumps(judgment), output=[])
    return cases, run, report, response


def test_judge_receives_reference_and_prediction_in_separate_request_and_resumes(tmp_path):
    cases, run, report, response = sample_data()
    client = Mock()
    client.responses.create.return_value = response
    path = tmp_path / "judge_results.json"
    collect_judgments(client, cases, run, report, path)
    request = client.responses.create.call_args.kwargs
    assert request["model"] == run["model"]
    assert request["input"][0] == {"role": "developer", "content": "Dedicated evaluator rules."}
    assert json.loads(request["input"][1]["content"]) == {
        "meeting_text": cases[0]["input"], "expected": cases[0]["expected"],
        "predicted": run["predictions"][0]["analysis"],
    }
    assert request["text"]["format"]["name"] == "meeting_judgment"
    assert request["text"]["format"]["strict"] is True and request["store"] is False
    original = path.read_bytes()
    collect_judgments(client, cases, run, report, path)
    assert client.responses.create.call_count == 1 and path.read_bytes() == original


@pytest.mark.parametrize("failure", ["malformed", "incomplete", "refusal", "duplicate", "out_of_bounds"])
def test_bad_judgment_is_saved_as_error_and_withholds_score(tmp_path, failure):
    cases, run, report, response = sample_data()
    if failure == "malformed":
        response.output_text = "not JSON"
    elif failure == "incomplete":
        response.status = "incomplete"
    elif failure == "refusal":
        response.output = [SimpleNamespace(type="message", content=[SimpleNamespace(type="refusal")])]
    else:
        value = json.loads(response.output_text)
        if failure == "duplicate":
            value["action_matches"] *= 2
        else:
            value["action_matches"][0]["predicted_index"] = 99
        response.output_text = json.dumps(value)
    client = Mock()
    client.responses.create.return_value = response
    collect_judgments(client, cases, run, report, tmp_path / "judge_results.json")
    assert report["judgments"][0]["status"] == "judge_error"
    _, summary = evaluate_predictions(cases, run, report["judgments"])
    assert summary["evaluation_status"] == "incomplete" and summary["f1"] is None


def test_resume_retries_only_failed_judgment_and_saves_safe_error(tmp_path):
    cases, run, report, response = sample_data()
    cases.append({**deepcopy(cases[0]), "id": "EXAMPLE-B"})
    run["predictions"].append({**deepcopy(run["predictions"][0]), "case_id": "EXAMPLE-B"})
    error = APIStatusError("dummy-secret must not be saved", response=httpx.Response(
        500, request=httpx.Request("POST", "https://example.invalid")), body=None)
    client = Mock()
    client.responses.create.side_effect = [response, error, response]
    path = tmp_path / "judge_results.json"
    collect_judgments(client, cases, run, report, path)
    assert "dummy-secret" not in path.read_text(encoding="utf-8")
    assert [row["status"] for row in report["judgments"]] == ["ok", "judge_error"]
    collect_judgments(client, cases, run, report, path)
    assert client.responses.create.call_count == 3
    assert all(row["status"] == "ok" for row in report["judgments"])


def test_failed_extraction_never_gets_sent_to_judge(tmp_path):
    cases, run, report, _ = sample_data()
    run["predictions"][0]["status"] = "api_error"
    client = Mock()
    collect_judgments(client, cases, run, report, tmp_path / "judge_results.json")
    client.responses.create.assert_not_called()
    summary = write_reports(tmp_path, cases, run, report)
    assert summary["missed_items"] == 1 and summary["f1"] == 0


def test_cli_requires_live_flag_then_reuses_complete_cache_offline(tmp_path):
    # A synthetic output against the real case IDs; no actual extraction or judgment.
    cases = json.loads(DATASET_PATH.read_bytes())
    output = {"summary": "Synthetic test output.", "decisions": [], "actions": []}
    run = {"model": MODEL, "prompt": "Test extraction rules.", "settings": {},
           "schema": MeetingAnalysis.model_json_schema(), "case_ids": [cases[0]["id"]],
           "dataset_sha256": hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
           "predictions": [{"case_id": cases[0]["id"], "status": "ok", "analysis": output}]}
    source = json.dumps(run).encode()
    (tmp_path / "predictions.json").write_bytes(source)
    command = [sys.executable, "-B", "-m", "week2.exercise.run_eval", str(tmp_path)]
    refused = subprocess.run(command, capture_output=True, text=True)
    assert refused.returncode != 0 and "No calls made" in refused.stderr
    assert not (tmp_path / "judge_results.json").exists()

    report = new_report(run, source, DATASET_PATH.read_bytes(), JUDGE_PROMPT_PATH.read_text(encoding="utf-8"))
    report["judgments"] = [{"case_id": cases[0]["id"], "status": "ok", "judgment": {
        "decision_matches": [], "action_matches": [], "summary_supported": False,
        "summary_complete": False, "notes": "Synthetic cache for offline CLI test.",
    }}]
    (tmp_path / "judge_results.json").write_text(json.dumps(report), encoding="utf-8")
    scored = subprocess.run(command, capture_output=True, text=True)
    assert scored.returncode == 0
    assert (tmp_path / "eval.csv").exists() and (tmp_path / "summary.csv").exists()
    with (tmp_path / "summary.csv").open(newline="", encoding="utf-8") as file:
        summary = next(csv.DictReader(file))
    assert summary["meetings"] == "1" and summary["extraction_failures"] == "0"
    expected_count = len(cases[0]["expected"]["decisions"]) + len(cases[0]["expected"]["actions"])
    assert int(summary["missed"]) == expected_count
    with (tmp_path / "eval.csv").open(newline="", encoding="utf-8") as file:
        comparisons = list(csv.DictReader(file))
    assert {row["case_id"] for row in comparisons} == {cases[0]["id"]}
    assert "Evaluating 1 case(s)" in scored.stdout
    original = (tmp_path / "judge_results.json").read_bytes()
    run["prompt"] = "Changed extraction prompt."
    (tmp_path / "predictions.json").write_text(json.dumps(run), encoding="utf-8")
    stale = subprocess.run(command, capture_output=True, text=True)
    assert stale.returncode != 0 and "different predictions/settings/prompt" in stale.stderr
    assert (tmp_path / "judge_results.json").read_bytes() == original


def test_reports_show_full_comparisons_and_compact_summary_with_details_in_json(tmp_path):
    cases, run, report, response = sample_data()
    client = Mock()
    client.responses.create.return_value = response
    collect_judgments(client, cases, run, report, tmp_path / "judge_results.json")
    summary = write_reports(tmp_path, cases, run, report)
    with (tmp_path / "eval.csv").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert list(rows[0]) == ["case_id", "item", "golden", "prediction", "result", "reason"]
    assert rows[0]["golden"] == cases[0]["expected"]["summary"]
    assert rows[-1]["golden"] == rows[-1]["prediction"]
    assert rows[-1]["result"] == "Correct" and rows[-1]["reason"] == "Same task."
    with (tmp_path / "summary.csv").open(newline="", encoding="utf-8") as file:
        compact = list(csv.DictReader(file))[0]
    assert len(compact) == 11 and compact["f1"] == "100.00%" and compact["correct"] == "1"
    assert "configuration" not in compact and "precision" not in compact
    saved = json.loads((tmp_path / "judge_results.json").read_text(encoding="utf-8"))
    assert saved["evaluation"] == summary and summary["precision"] == 1.0
    assert client.responses.create.call_count == 1
