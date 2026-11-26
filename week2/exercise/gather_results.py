"""Combine selected evaluated runs and calculate overall F1. No model calls."""

import argparse
import csv
import hashlib
import json

from week2.exercise.evaluate import evaluate_predictions, format_f1, metrics, summary_row
from week2.exercise.run_cases import DATASET_PATH, REPORTS_DIR, load_run_cases
from week2.exercise.run_eval import configuration_key, fingerprint, write_csv


def gather_results(run_names: list[str]) -> tuple[list[dict], list[dict]]:
    if not run_names or len(run_names) != len(set(run_names)):
        raise ValueError("Choose at least one run folder, with no duplicates.")
    results = []
    groups = {}
    seen_predictions = set()
    for run_name in run_names:
        run_dir = REPORTS_DIR / run_name
        if run_dir.name != run_name:
            raise ValueError("Use run folder names inside week2/reports.")
        with (run_dir / "summary.csv").open(newline="", encoding="utf-8") as file:
            summaries = list(csv.DictReader(file))
        if len(summaries) != 1:
            raise ValueError(f"Expected one summary row: {run_name}")
        csv_row = summaries[0]
        predictions_bytes = (run_dir / "predictions.json").read_bytes()
        source_hash = hashlib.sha256(predictions_bytes).hexdigest()
        report = json.loads((run_dir / "judge_results.json").read_text(encoding="utf-8"))
        run = json.loads(predictions_bytes)
        dataset_bytes, cases = load_run_cases(run, DATASET_PATH)
        dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()
        configuration = configuration_key(report)
        source_id = (source_hash, configuration)
        if source_id in seen_predictions:
            raise ValueError("The same extraction run was selected more than once.")
        seen_predictions.add(source_id)
        saved_summary = report.get("evaluation", {})
        if (saved_summary.get("predictions_sha256") != source_hash
                or report["metadata"]["predictions_sha256"] != source_hash
                or report["metadata"]["dataset_sha256"] != dataset_hash
                or saved_summary.get("judgments_sha256") != fingerprint(report["judgments"])
                or saved_summary.get("configuration") != configuration):
            raise ValueError(f"Source data changed; regenerate the evaluation: {run_name}")
        # Confirm the CSV still describes the saved judgments. This is offline arithmetic.
        _, scores = evaluate_predictions(cases, run, report["judgments"])
        row = {"run": run_name, "configuration": configuration,
               "model": report["metadata"]["judge"]["model"], **scores,
               "predictions_sha256": source_hash, "judgments_sha256": fingerprint(report["judgments"])}
        expected_csv = {key: "" if value is None else str(value) for key, value in summary_row(row).items()}
        if saved_summary != row or csv_row != expected_csv:
            raise ValueError(f"Summary differs from saved judgments: {run_name}")
        results.append(row)
        groups.setdefault(row["configuration"], []).append(row)

    overall = []
    for configuration, rows in groups.items():
        incomplete = sum(row["evaluation_status"] != "complete" for row in rows)
        successful = sum(int(row["successful_cases"]) for row in rows)
        attempts = sum(int(row["case_count"]) for row in rows)
        combined = {
            "configuration": configuration[:12], "model": rows[0]["model"], "runs": len(rows),
            "run_folders": " ".join(row["run"] for row in rows),
            "cases_per_run": int(rows[0]["case_count"]),
            "case_attempts": attempts, "successful_cases": successful,
            "schema_compliance_of_successes": 1.0 if successful else None,
            "successful_attempt_rate": successful / attempts,
            "summary_supported_count": sum(int(row["summary_supported_count"]) for row in rows),
            "summary_complete_count": sum(int(row["summary_complete_count"]) for row in rows),
            "summaries_needing_review": sum(row["summaries_needing_review"] for row in rows),
            "extraction_failures": sum(int(row["extraction_failures"]) for row in rows),
            "judge_errors": sum(int(row["judge_errors"]) for row in rows),
            "evaluation_status": "incomplete" if incomplete else "complete",
            "correct_items": None, "extra_items": None, "missed_items": None,
            "precision": None, "recall": None, "f1": None, "f1_target_met": None,
            "review_basis": "model_judged",
        }
        if not incomplete:
            counts = {name: sum(int(row[f"{name}_items"]) for row in rows)
                      for name in ["correct", "extra", "missed"]}
            score = metrics(**counts)
            combined.update({f"{name}_items": counts[name] for name in counts})
            combined.update({name: score[name] for name in ["precision", "recall", "f1"]})
            combined["f1_target_met"] = score["f1"] is not None and score["f1"] >= 0.85
        overall.append(combined)
    return results, overall


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="*", help="Run folder names inside week2/reports.")
    args = parser.parse_args()
    run_names = args.runs or input("Run folders inside week2/reports (separated by spaces): ").split()
    try:
        results, overall = gather_results(run_names)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    write_csv(REPORTS_DIR / "all_run_results.csv", [
        {"configuration": row["configuration"][:12], "model": row["model"], **summary_row(row)} for row in results
    ])
    write_csv(REPORTS_DIR / "results.csv", [{
        "configuration": row["configuration"], "model": row["model"], "runs": row["runs"],
        "meetings": row["case_attempts"], "valid_outputs": row["successful_cases"],
        "correct": row["correct_items"], "extra": row["extra_items"], "missed": row["missed_items"],
        "f1": format_f1(row["f1"]), "summaries_needing_review": row["summaries_needing_review"],
        "extraction_failures": row["extraction_failures"], "judge_errors": row["judge_errors"],
        "status": row["evaluation_status"],
    } for row in overall])
    print(f"Saved: {REPORTS_DIR / 'all_run_results.csv'}")
    print(f"Saved: {REPORTS_DIR / 'results.csv'}")


if __name__ == "__main__":
    main()
