"""Check overall CSV results with invented runs and no provider client."""

import csv
import json
from copy import deepcopy

import pytest

from app.schemas import MeetingAnalysis
from week2.exercise import gather_results as gather
from week2.exercise.run_eval import new_report, write_reports


@pytest.fixture
def experiment(tmp_path, monkeypatch):
    output = {"summary": "Nira will update tests.", "decisions": [],
              "actions": [{"owner": "Nira", "action": "Update tests", "due_date": None}]}
    cases = [{"id": name, "input": "Nira will update tests.", "expected": deepcopy(output)} for name in ["A", "B"]]
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(cases), encoding="utf-8")
    monkeypatch.setattr(gather, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(gather, "DATASET_PATH", dataset)
    return tmp_path, cases, dataset


def save_run(experiment, name, *, poor=False, incomplete=False, all_judges_failed=False, prompt="Same extraction rules.",
             judge_prompt="Same evaluator rules."):
    root, cases, dataset = experiment
    folder = root / name
    folder.mkdir()
    predictions = []
    judgments = []
    for index, case in enumerate(cases):
        output = deepcopy(case["expected"])
        matches = [{"expected_index": 0, "predicted_index": 0, "reason": "Same task."}]
        if poor:
            if index == 0:
                output["actions"].extend([
                    {"owner": "Nira", "action": "Invented deployment", "due_date": None},
                    {"owner": "Nira", "action": "Invented migration", "due_date": None},
                ])
            else:
                output["actions"] = []
                matches = []
        predictions.append({"case_id": case["id"], "status": "ok", "analysis": output, "model": "mock-model"})
        judgments.append({"case_id": case["id"], "status": "ok", "model": "mock-model", "judgment": {
            "decision_matches": [], "action_matches": matches, "summary_supported": not poor,
            "summary_complete": not poor, "notes": "Invented run for aggregation tests.",
        }})
    if incomplete:
        judgments[-1] = {"case_id": "B", "status": "judge_error", "error": "Simulated failure."}
    if all_judges_failed:
        judgments = [{"case_id": case["id"], "status": "judge_error", "error": "Simulated failure."} for case in cases]
    run = {"run_id": name, "model": "mock-model", "prompt": prompt, "settings": {},
           "schema": MeetingAnalysis.model_json_schema(), "case_ids": ["A", "B"], "predictions": predictions}
    source = json.dumps(run).encode()
    (folder / "predictions.json").write_bytes(source)
    report = new_report(run, source, dataset.read_bytes(), judge_prompt)
    report["judgments"] = judgments
    write_reports(folder, cases, run, report)
    return folder


def test_overall_f1_uses_combined_counts_not_mean_run_percentages(experiment):
    save_run(experiment, "run-1")  # correct 2, extra 0, missed 0: F1 1.0
    save_run(experiment, "run-2", poor=True)  # correct 1, extra 2, missed 1: F1 0.4
    rows, overall = gather.gather_results(["run-1", "run-2"])
    assert len(rows) == 2 and len(overall) == 1
    result = overall[0]
    assert result["correct_items"] == 3 and result["extra_items"] == 2 and result["missed_items"] == 1
    assert result["f1"] == 2 / 3 and result["f1"] != 0.7
    assert result["runs"] == 2 and result["case_attempts"] == 4


def test_incomplete_run_remains_visible_and_withholds_group_score(experiment):
    save_run(experiment, "run-1")
    save_run(experiment, "run-2", incomplete=True)
    rows, overall = gather.gather_results(["run-1", "run-2"])
    assert len(rows) == 2 and len(overall) == 1
    assert overall[0]["evaluation_status"] == "incomplete"
    assert overall[0]["judge_errors"] == 1 and overall[0]["f1"] is None


def test_run_with_no_returned_judge_models_still_blocks_its_configuration_group(experiment):
    save_run(experiment, "run-1")
    save_run(experiment, "run-2", all_judges_failed=True)
    rows, overall = gather.gather_results(["run-1", "run-2"])
    assert len(rows) == 2 and len(overall) == 1
    assert overall[0]["runs"] == 2 and overall[0]["judge_errors"] == 2
    assert overall[0]["evaluation_status"] == "incomplete" and overall[0]["f1"] is None


def test_different_prompt_configurations_are_reported_separately(experiment):
    save_run(experiment, "run-1")
    save_run(experiment, "run-2", prompt="Different extraction rules.")
    _, overall = gather.gather_results(["run-1", "run-2"])
    assert len(overall) == 2 and all(row["runs"] == 1 for row in overall)


def test_different_judge_prompts_are_reported_separately(experiment):
    save_run(experiment, "run-1")
    save_run(experiment, "run-2", judge_prompt="Different evaluation rules.")
    _, overall = gather.gather_results(["run-1", "run-2"])
    assert len(overall) == 2


def test_copied_predictions_can_compare_judges_but_cannot_count_twice_in_same_group(experiment):
    root, cases, dataset = experiment
    original = save_run(experiment, "run-1")
    copied = root / "run-copy"
    copied.mkdir()
    for name in ["predictions.json", "judge_results.json", "summary.csv"]:
        (copied / name).write_bytes((original / name).read_bytes())
    with pytest.raises(ValueError, match="same extraction run"):
        gather.gather_results(["run-1", "run-copy"])
    source = (copied / "predictions.json").read_bytes()
    run = json.loads(source)
    report = new_report(run, source, dataset.read_bytes(), "Changed judge rules.")
    report["judgments"] = json.loads((original / "judge_results.json").read_bytes())["judgments"]
    write_reports(copied, cases, run, report)
    _, overall = gather.gather_results(["run-1", "run-copy"])
    assert len(overall) == 2


def test_selected_runs_must_be_unique_and_nonempty(experiment):
    with pytest.raises(ValueError, match="at least one"):
        gather.gather_results([])
    with pytest.raises(ValueError, match="duplicates"):
        gather.gather_results(["run-1", "run-1"])


def test_changed_predictions_or_summary_are_rejected(experiment):
    folder = save_run(experiment, "run-1")
    source = folder / "predictions.json"
    original = source.read_bytes()
    source.write_bytes(original + b" ")
    with pytest.raises(ValueError, match="changed"):
        gather.gather_results(["run-1"])
    source.write_bytes(original)
    summary_path = folder / "summary.csv"
    with summary_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    rows[0]["f1"] = "0.123"
    with summary_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="differs"):
        gather.gather_results(["run-1"])


def test_cli_writes_both_final_csvs_offline(experiment, monkeypatch):
    root, _, _ = experiment
    save_run(experiment, "run-1")
    monkeypatch.setattr("sys.argv", ["gather_results", "run-1"])
    gather.main()
    with (root / "results.csv").open(newline="", encoding="utf-8") as file:
        result = list(csv.DictReader(file))
    assert len(result) == 1 and result[0]["f1"] == "100.00%"
    assert result[0]["correct"] == "2" and "precision" not in result[0]
    assert (root / "all_run_results.csv").exists()


def test_changed_judgment_reason_requires_regeneration_even_if_counts_are_unchanged(experiment):
    folder = save_run(experiment, "run-1")
    path = folder / "judge_results.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["judgments"][0]["judgment"]["action_matches"][0]["reason"] = "Edited explanation."
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        gather.gather_results(["run-1"])


def test_incomplete_group_csv_keeps_score_blank_and_errors_visible(experiment, monkeypatch):
    root, _, _ = experiment
    save_run(experiment, "run-1", incomplete=True)
    monkeypatch.setattr("sys.argv", ["gather_results", "run-1"])
    gather.main()
    with (root / "results.csv").open(newline="", encoding="utf-8") as file:
        result = list(csv.DictReader(file))[0]
    assert result["f1"] == result["correct"] == ""
    assert result["status"] == "incomplete" and result["judge_errors"] == "1"


def test_single_case_run_is_scored_alone_and_not_pooled_with_full_runs(experiment):
    root, cases, dataset = experiment
    save_run(experiment, "full-run")
    folder = save_run(experiment, "single-run")
    run = json.loads((folder / "predictions.json").read_text(encoding="utf-8"))
    run["case_ids"] = ["A"]
    run["predictions"] = run["predictions"][:1]
    source = json.dumps(run).encode()
    (folder / "predictions.json").write_bytes(source)
    old_report = json.loads((folder / "judge_results.json").read_text(encoding="utf-8"))
    report = new_report(run, source, dataset.read_bytes(), "Same evaluator rules.")
    report["judgments"] = old_report["judgments"][:1]
    write_reports(folder, cases[:1], run, report)
    rows, groups = gather.gather_results(["full-run", "single-run"])
    assert sorted(row["case_count"] for row in rows) == [1, 2]
    assert len(groups) == 2 and sorted(group["case_attempts"] for group in groups) == [1, 2]
    assert all(group["f1"] == 1.0 and group["extraction_failures"] == 0 for group in groups)
