"""Exercise the collection/scoring flow with invented data and simulated responses."""

import csv
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APIStatusError

# Match running the scripts directly from their exercise directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_cases import collect_predictions
from run_eval import evaluate_predictions, write_csv


def test_collection_records_failures_and_keeps_gold_labels_out_of_requests(tmp_path):
    cases = []
    for number in range(5):
        cases.append({
            "issue_id": f"DEMO-{number}", "text": f"Synthetic issue {number}",
            "category": "Bug", "priority": "P1",
        })
    output = '{"category":"Question","priority":"P3","next_actions":["Ask for context."]}'
    completed = SimpleNamespace(
        output_text=output, status="completed", id="resp_mock", model="mock-model", usage=None,
    )
    invalid = SimpleNamespace(
        output_text="not JSON", status="completed", id="resp_invalid", model="mock-model", usage=None,
    )
    incomplete = SimpleNamespace(
        output_text=output, status="incomplete", id="resp_incomplete", model="mock-model", usage=None,
    )
    api_error = APIStatusError(
        "Dummy secret must not be saved: test-secret",
        response=httpx.Response(429, request=httpx.Request("POST", "https://example.invalid")),
        body=None,
    )
    client = Mock()
    client.responses.create.side_effect = [completed, invalid, api_error, incomplete, completed]
    run = {"model": "mock-model", "prompts": {"v1": "Test rules."}, "predictions": []}
    report_path = tmp_path / "predictions.json"

    collect_predictions(client, cases, run, report_path)

    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert [row["status"] for row in saved["predictions"]] == [
        "ok", "invalid_output", "api_error", "response_error", "ok",
    ]
    assert saved["predictions"][1]["raw_output"] == "not JSON"
    assert "test-secret" not in report_path.read_text(encoding="utf-8")
    assert client.responses.create.call_count == 5
    for case, request in zip(cases, client.responses.create.call_args_list):
        assert request.kwargs["input"] == [
            {"role": "developer", "content": "Test rules."},
            {"role": "user", "content": case["text"]},
        ]


def test_scoring_matches_ids_and_keeps_failed_or_missing_cases_in_denominator(tmp_path):
    cases = [
        {"issue_id": "A", "text": "First issue", "category": "Bug", "priority": "P1"},
        {"issue_id": "B", "text": "Second issue", "category": "Feature", "priority": "P3"},
        {"issue_id": "C", "text": "Third issue", "category": "Risk", "priority": "P2"},
        {"issue_id": "D", "text": "Fourth issue", "category": "Bug", "priority": "P1"},
    ]
    run = {
        "model": "mock-model", "prompts": {"v1": "Test rules.", "v2": "Other rules."},
        "predictions": [
            {"prompt_version": "v1", "issue_id": "C", "status": "ok", "error": "",
             "classification": {"category": "Risk", "priority": "P3"}},
            {"prompt_version": "v1", "issue_id": "B", "status": "api_error", "error": "HTTP 429",
             "classification": None},
            {"prompt_version": "v1", "issue_id": "A", "status": "ok", "error": "",
             "classification": {"category": "Bug", "priority": "P1"}},
        ],
    }

    rows, summaries = evaluate_predictions(run, cases)

    assert len(rows) == 8 and len(summaries) == 2
    assert summaries[0]["category_accuracy"] == 2 / 4
    assert summaries[0]["priority_accuracy"] == 1 / 4
    assert summaries[0]["api_errors"] == 1
    assert summaries[0]["missing_cases"] == 1
    assert summaries[0]["critical_p1_miss_ids"] == '["D"]'
    assert summaries[1]["missing_cases"] == 4
    assert summaries[1]["category_accuracy"] == 0
    assert summaries[1]["critical_p1_miss_count"] == 2

    write_csv(tmp_path / "eval.csv", rows)
    write_csv(tmp_path / "summary.csv", summaries)
    with (tmp_path / "eval.csv").open(newline="", encoding="utf-8") as file:
        saved_rows = list(csv.DictReader(file))
    assert len(saved_rows) == 8
    assert saved_rows[0]["predicted_category"] == "Bug"
    assert saved_rows[3]["status"] == "missing"


def test_scoring_rejects_duplicate_or_unknown_predictions():
    cases = [{"issue_id": "A", "text": "Issue", "category": "Bug", "priority": "P1"}]
    prediction = {"prompt_version": "v1", "issue_id": "A", "status": "api_error", "error": "HTTP 429"}
    run = {"model": "mock-model", "prompts": {"v1": "Rules"}, "predictions": [prediction, prediction]}
    with pytest.raises(ValueError, match="Duplicate"):
        evaluate_predictions(run, cases)

    run["predictions"] = [{**prediction, "issue_id": "UNKNOWN"}]
    with pytest.raises(ValueError, match="Unexpected"):
        evaluate_predictions(run, cases)


def test_scoring_matches_the_supplied_scorer(tmp_path):
    project_root = Path(__file__).resolve().parents[3]
    gold_path = project_root / "data" / "evaluation" / "issue_classification_hidden.json"
    cases = json.loads(gold_path.read_text(encoding="utf-8"))
    run = {"model": "OFFLINE SCORER CHECK", "prompts": {"test": "Not sent to a model."}, "predictions": []}
    for index, case in enumerate(cases):
        # Invent mixed correct/incorrect predictions solely to compare scorer arithmetic.
        prediction = {
            "prompt_version": "test", "issue_id": case["issue_id"], "status": "ok", "error": "",
            "classification": {"category": case["category"], "priority": case["priority"]},
        }
        if index % 4 == 0:
            prediction["status"] = "invalid_output"
            prediction["classification"] = None
        elif index % 3 == 0:
            prediction["classification"]["category"] = "Question"
            prediction["classification"]["priority"] = "P3"
        run["predictions"].append(prediction)

    rows, summaries = evaluate_predictions(run, cases)
    csv_path = tmp_path / "synthetic_predictions.csv"
    write_csv(csv_path, rows)
    result = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "evaluate_issue_classifier.py"), str(csv_path)],
        capture_output=True, text=True, check=True,
    )
    summary = summaries[0]
    total = len(cases)
    assert f"Category accuracy: {summary['category_correct']}/{total} = {summary['category_accuracy']:.1%}" in result.stdout
    assert f"Priority accuracy: {summary['priority_correct']}/{total} = {summary['priority_accuracy']:.1%}" in result.stdout
    assert f"Critical P1 misses: {json.loads(summary['critical_p1_miss_ids'])}" in result.stdout
