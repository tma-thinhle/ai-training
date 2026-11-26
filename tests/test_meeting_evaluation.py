"""Check scoring and collection with invented data; no model calls."""

import json
import subprocess
import sys
from copy import deepcopy

import httpx
import pytest

from app.schemas import MeetingAnalysis
from week2.exercise.evaluate import comparison_rows, count_matches, evaluate_predictions, metrics
from week2.exercise.run_cases import DATASET_PATH, PROJECT_ROOT, collect_predictions, load_run_cases, select_cases


def sample_case(case_id="EXAMPLE-A") -> dict:
    return {"id": case_id, "input": "Nira will update checkout tests. No deadline was set.", "expected": {
        "summary": "Nira will update checkout tests.", "decisions": [],
        "actions": [{"owner": "Nira", "action": "Update checkout tests", "due_date": None}],
    }}


def judged_match(case_id="EXAMPLE-A") -> dict:
    return {
        "case_id": case_id, "status": "ok", "judgment": {
            "decision_matches": [],
            "action_matches": [{"expected_index": 0, "predicted_index": 0, "reason": "Same task."}],
            "summary_supported": True, "summary_complete": True,
            "notes": "Invented judgment for an offline arithmetic test.",
        },
    }


def test_paraphrase_uses_semantic_match_and_extra_items_reduce_precision():
    case = sample_case()
    output = deepcopy(case["expected"])
    output["actions"][0]["action"] = "Revise the checkout test suite"
    output["actions"].append({"owner": "Nira", "action": "Deploy checkout", "due_date": None})
    run = {"predictions": [{"case_id": case["id"], "status": "ok", "analysis": output}]}
    rows, summary = evaluate_predictions([case], run, [judged_match()])
    assert rows[0]["correct_items"] == 1 and rows[0]["extra_items"] == 1
    assert summary["precision"] == 0.5 and summary["recall"] == 1.0
    assert summary["f1"] == 2 / 3 and summary["review_basis"] == "model_judged"


@pytest.mark.parametrize("field,value", [("owner", "Other person"), ("due_date", "2026-12-01")])
def test_wrong_owner_or_date_counts_as_extra_and_missed(field, value):
    case = sample_case()
    output = deepcopy(case["expected"])
    output["actions"][0][field] = value
    run = {"predictions": [{"case_id": case["id"], "status": "ok", "analysis": output}]}
    _, summary = evaluate_predictions([case], run, [judged_match()])
    assert summary["correct_items"] == 0
    assert summary["extra_items"] == 1 and summary["missed_items"] == 1
    assert summary["f1"] == 0.0


def test_failed_missing_and_empty_cases_remain_visible():
    cases = [sample_case("A"), sample_case("B"), sample_case("C"), sample_case("D")]
    cases[3]["expected"]["actions"] = []
    run = {"predictions": [
        {"case_id": "A", "status": "ok", "analysis": cases[0]["expected"]},
        {"case_id": "B", "status": "api_error"},
        {"case_id": "D", "status": "response_error"},
    ]}
    rows, summary = evaluate_predictions(cases, run, [judged_match("A")])
    assert [row["extraction_status"] for row in rows] == ["ok", "api_error", "missing", "response_error"]
    assert summary["correct_items"] == 1 and summary["missed_items"] == 2
    assert summary["recall"] == 1 / 3
    assert summary["case_count"] == 4 and summary["extraction_failures"] == 3


def test_empty_reference_does_not_hide_invented_decisions():
    case = sample_case()
    case["expected"]["actions"] = []
    output = {**case["expected"], "decisions": ["Deploy immediately."]}
    judge = judged_match()
    judge["judgment"].update(action_matches=[], summary_supported=False)
    _, summary = evaluate_predictions([case], {"predictions": [
        {"case_id": case["id"], "status": "ok", "analysis": output},
    ]}, [judge])
    assert summary["extra_items"] == 1 and summary["f1"] == 0
    assert summary["summary_supported_count"] == 0


def test_decisions_are_matched_by_recorded_meaning_not_order():
    case = sample_case()
    case["expected"]["decisions"] = ["Keep the existing checkout.", "Delay deployment."]
    output = deepcopy(case["expected"])
    output["decisions"] = ["Postpone deployment.", "Retain checkout as it is."]
    judge = judged_match()
    judge["judgment"]["decision_matches"] = [
        {"expected_index": 0, "predicted_index": 1, "reason": "Same design decision."},
        {"expected_index": 1, "predicted_index": 0, "reason": "Same postponement."},
    ]
    _, summary = evaluate_predictions([case], {"predictions": [
        {"case_id": case["id"], "status": "ok", "analysis": output},
    ]}, [judge])
    assert summary["decisions_correct"] == 2 and summary["f1"] == 1.0


@pytest.mark.parametrize("judgments", [[], [{"case_id": "EXAMPLE-A", "status": "judge_error", "error": "Simulated timeout"}]])
def test_unresolved_judge_withholds_final_score_instead_of_dropping_case(judgments):
    case = sample_case()
    run = {"predictions": [{"case_id": case["id"], "status": "ok", "analysis": case["expected"]}]}
    rows, summary = evaluate_predictions([case], run, judgments)
    assert len(rows) == 1 and rows[0]["judge_status"] == "judge_error"
    assert rows[0]["correct_items"] is None
    assert summary["evaluation_status"] == "incomplete" and summary["judge_errors"] == 1
    assert summary["f1"] is None and summary["f1_target_met"] is None


def test_duplicate_match_cannot_inflate_score():
    case = sample_case()
    matches = judged_match()["judgment"]["action_matches"] * 2
    with pytest.raises(ValueError, match="twice"):
        count_matches(case["expected"]["actions"], case["expected"]["actions"], matches, actions=True)


@pytest.mark.parametrize("case_ids", [["EXAMPLE-A", "EXAMPLE-A"], ["UNKNOWN"]])
def test_duplicate_or_unknown_predictions_are_rejected(case_ids):
    run = {"predictions": [{"case_id": case_id, "status": "api_error"} for case_id in case_ids]}
    with pytest.raises(ValueError, match="Unknown or duplicate"):
        evaluate_predictions([sample_case()], run, [])


def test_invalid_saved_judgment_is_visible_as_error_not_a_score():
    case = sample_case()
    judge = judged_match()
    judge["judgment"]["action_matches"][0]["expected_index"] = 99
    _, summary = evaluate_predictions([case], {"predictions": [
        {"case_id": case["id"], "status": "ok", "analysis": case["expected"]},
    ]}, [judge])
    assert summary["judge_errors"] == 1 and summary["f1"] is None


def test_all_failed_run_does_not_claim_schema_success():
    _, summary = evaluate_predictions([sample_case()], {"predictions": []}, [])
    assert summary["schema_compliance_of_successes"] is None
    assert summary["missed_items"] == 1 and summary["f1"] == 0
    assert summary["f1_target_met"] is False
    assert metrics(0, 0, 0)["f1"] is None


def test_supplied_references_fit_the_contract_without_changing_them():
    path = PROJECT_ROOT / "data/week2/week2_meeting_notes_expected_20_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert len(cases) == 20 and len({case["id"] for case in cases}) == 20
    for case in cases:
        MeetingAnalysis.model_validate(case["expected"])


def test_collection_calls_http_route_and_excludes_gold_from_requests():
    cases = [sample_case(f"EXAMPLE-{index}") for index in range(4)]
    requests = []
    statuses = iter([200, 502, 504, 503])
    def respond(request):
        requests.append(request)
        return httpx.Response(next(statuses), json={"detail": "Fake API response"})
    with httpx.Client(base_url="http://example.invalid", transport=httpx.MockTransport(respond)) as client:
        collect_predictions(client, cases, {"run_id": "fake-run"})
    assert len(requests) == 4
    for case, request in zip(cases, requests):
        assert request.method == "POST" and request.url.path == "/analyze-meeting"
        assert json.loads(request.content) == {"meeting_text": case["input"]}
        assert request.headers["X-Run-ID"] == "fake-run" and request.headers["X-Case-ID"] == case["id"]


def test_collector_cli_requires_live_flag_before_any_call_or_output():
    result = subprocess.run([sys.executable, "-B", "-m", "week2.exercise.run_cases"],
                            capture_output=True, text=True)
    assert result.returncode != 0 and "No requests sent" in result.stderr


def test_comparisons_align_meaning_and_show_missed_and_extra_items():
    case = sample_case()
    case["expected"]["decisions"] = ["Keep checkout.", "Delay deployment.", "Keep the current database."]
    output = deepcopy(case["expected"])
    output["decisions"] = ["Postpone deployment.", "Retain checkout.", "Approve an unrelated feature."]
    judge = judged_match()
    judge["judgment"]["decision_matches"] = [
        {"expected_index": 0, "predicted_index": 1, "reason": "Same checkout decision."},
        {"expected_index": 1, "predicted_index": 0, "reason": "Same deployment decision."},
    ]
    run = {"predictions": [{"case_id": case["id"], "status": "ok", "analysis": output}]}
    statuses, summary = evaluate_predictions([case], run, [judge])
    rows = comparison_rows([case], run, [judge], statuses)
    decisions = [row for row in rows if row["item"] == "Decision"]
    assert list(rows[0]) == ["case_id", "item", "golden", "prediction", "result", "reason"]
    assert decisions[0]["golden"] == "Keep checkout." and decisions[0]["prediction"] == "Retain checkout."
    assert decisions[1]["prediction"] == "Postpone deployment."
    assert decisions[2]["result"] == "Missed" and decisions[2]["prediction"] == ""
    assert decisions[3]["result"] == "Extra" and decisions[3]["golden"] == ""
    assert summary["correct_items"] == 3 and summary["extra_items"] == summary["missed_items"] == 1


@pytest.mark.parametrize("field,value", [("owner", "Omar"), ("due_date", "2026-12-01")])
def test_action_comparison_explains_exact_field_difference(field, value):
    case = sample_case()
    output = deepcopy(case["expected"])
    output["actions"][0][field] = value
    run = {"predictions": [{"case_id": case["id"], "status": "ok", "analysis": output}]}
    statuses, summary = evaluate_predictions([case], run, [judged_match()])
    rows = comparison_rows([case], run, [judged_match()], statuses)
    action = next(row for row in rows if row["item"] == "Action")
    assert action["result"] == "Incorrect"
    assert field.replace("_", " ") + " differs" in action["reason"]
    assert value in action["prediction"] and "owner:" in action["golden"] and "due:" in action["golden"]
    assert "one extra and one missed" in action["reason"]
    assert summary["extra_items"] == summary["missed_items"] == 1


def test_summary_comparison_explains_issues_without_affecting_extraction_score():
    case = sample_case()
    judge = judged_match()
    judge["judgment"].update(summary_supported=False, summary_complete=False, notes="The summary invents a deployment and omits testing.")
    run = {"predictions": [{"case_id": case["id"], "status": "ok", "analysis": case["expected"]}]}
    statuses, summary = evaluate_predictions([case], run, [judge])
    row = comparison_rows([case], run, [judge], statuses)[0]
    assert row["result"] == "Needs review"
    assert "Unsupported" in row["reason"] and "missing" in row["reason"] and "deployment" in row["reason"]
    assert summary["summaries_needing_review"] == 1 and summary["f1"] == 1.0


def test_failed_extraction_comparison_shows_missing_items_not_false_empty_success():
    case = sample_case()
    run = {"predictions": []}
    statuses, summary = evaluate_predictions([case], run, [])
    rows = comparison_rows([case], run, [], statuses)
    assert rows[0]["result"] == "Extraction failed"
    assert next(row for row in rows if row["item"] == "Action")["result"] == "Missed"
    assert next(row for row in rows if row["item"] == "Decision")["result"] == "Extraction failed"
    assert summary["missed_items"] == 1


def test_judge_error_comparison_does_not_invent_matches_or_item_verdicts():
    case = sample_case()
    run = {"predictions": [{"case_id": case["id"], "status": "ok", "analysis": case["expected"]}]}
    statuses, summary = evaluate_predictions([case], run, [])
    rows = comparison_rows([case], run, [], statuses)
    assert all(row["result"] == "Not evaluated" for row in rows)
    assert rows[-1]["golden"] == rows[-1]["prediction"]
    assert summary["f1"] is None and summary["summaries_needing_review"] == 0


def test_correctly_empty_comparison_rows_do_not_add_scored_items():
    case = sample_case()
    case["expected"]["actions"] = []
    judge = judged_match()
    judge["judgment"]["action_matches"] = []
    run = {"predictions": [{"case_id": case["id"], "status": "ok", "analysis": case["expected"]}]}
    statuses, summary = evaluate_predictions([case], run, [judge])
    rows = comparison_rows([case], run, [judge], statuses)
    assert [row["result"] for row in rows] == ["Correct", "Correctly empty", "Correctly empty"]
    assert summary["correct_items"] == 0 and summary["f1"] is None


@pytest.mark.parametrize("case_ids", [[], ["UNKNOWN"], ["A", "A"], "A", [123]])
def test_invalid_saved_case_selection_is_rejected(case_ids):
    with pytest.raises(ValueError):
        select_cases([sample_case("A"), sample_case("B")], case_ids)


def test_single_case_selection_keeps_failures_inside_that_scope():
    cases = select_cases([sample_case("A"), sample_case("B")], ["B"])
    _, summary = evaluate_predictions(cases, {"predictions": []}, [])
    assert summary["case_count"] == 1 and summary["extraction_failures"] == 1
    assert summary["missed_items"] == 1


def test_saved_dataset_path_is_used_instead_of_current_collector_setting(tmp_path):
    recorded = "data/week2/week2_meeting_notes_expected_20_cases.json"
    source, cases = load_run_cases({"dataset": recorded, "case_ids": ["TC15"]}, tmp_path / "not-the-saved-dataset.json")
    assert source == (PROJECT_ROOT / recorded).read_bytes()
    assert [case["id"] for case in cases] == ["TC15"]
    assert len(select_cases(json.loads(source), None)) == 20


def test_saved_dataset_cannot_escape_repository():
    with pytest.raises(ValueError, match="inside the repository"):
        load_run_cases({"dataset": "../outside.json"}, DATASET_PATH)
