"""Score saved predictions against gold labels without calling the model."""

import csv
import json
from pathlib import Path

EXERCISE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXERCISE_DIR.parent.parent
GOLD_PATH = PROJECT_ROOT / "data" / "evaluation" / "issue_classification_gold.json"
REPORTS_DIR = EXERCISE_DIR.parent / "reports"


def evaluate_predictions(run: dict, cases: list[dict]) -> tuple[list[dict], list[dict]]:
    gold_by_id = {}
    for case in cases:
        gold_by_id[case["issue_id"]] = case

    predictions_by_key = {}
    for prediction in run["predictions"]:
        version = prediction["prompt_version"]
        issue_id = prediction["issue_id"]
        key = (version, issue_id)
        if version not in run["prompts"] or issue_id not in gold_by_id:
            raise ValueError(f"Unexpected prediction: {key}")
        if key in predictions_by_key:
            raise ValueError(f"Duplicate prediction: {key}")
        predictions_by_key[key] = prediction

    rows = []
    summaries = []
    for version in run["prompts"]:
        category_correct = 0
        priority_correct = 0
        p1_misses = []
        status_counts = {"ok": 0, "invalid_output": 0, "api_error": 0, "response_error": 0, "missing": 0}
        for case in cases:
            prediction = predictions_by_key.get((version, case["issue_id"]))
            status = "missing"
            classification = {}
            error = "No saved prediction."
            if prediction is not None:
                status = prediction["status"]
                error = prediction["error"]
                if status == "ok":
                    classification = prediction["classification"]

            category = classification.get("category", "")
            priority = classification.get("priority", "")
            row = {
                "prompt_version": version,
                "issue_id": case["issue_id"],
                "text": case["text"],
                "status": status,
                "schema_valid": status == "ok",
                "expected_category": case["category"],
                "predicted_category": category,
                "category_correct": category == case["category"],
                "expected_priority": case["priority"],
                "predicted_priority": priority,
                "priority_correct": priority == case["priority"],
                "critical_p1_miss": case["priority"] == "P1" and priority != "P1",
                "error": error,
            }
            rows.append(row)
            status_counts[status] += 1
            if row["category_correct"]:
                category_correct += 1
            if row["priority_correct"]:
                priority_correct += 1
            if row["critical_p1_miss"]:
                p1_misses.append(row["issue_id"])

        total = len(cases)
        valid_count = status_counts["ok"]

        summaries.append({
            "prompt_version": version,
            "model": run["model"],
            "case_count": total,
            "category_correct": category_correct,
            "category_accuracy": category_correct / total,
            "priority_correct": priority_correct,
            "priority_accuracy": priority_correct / total,
            "schema_valid_count": valid_count,
            "schema_valid_rate": valid_count / total,
            "failed_cases": total - valid_count,
            "invalid_outputs": status_counts["invalid_output"],
            "api_errors": status_counts["api_error"],
            "response_errors": status_counts["response_error"],
            "missing_cases": status_counts["missing"],
            "critical_p1_miss_count": len(p1_misses),
            "critical_p1_miss_ids": json.dumps(p1_misses),
        })

    return rows, summaries


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    run_id = input("Run folder name (inside week1/reports): ").strip()
    run_dir = REPORTS_DIR / run_id
    run = json.loads((run_dir / "predictions.json").read_text(encoding="utf-8"))
    cases = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

    rows, summaries = evaluate_predictions(run, cases)
    write_csv(run_dir / "eval.csv", rows)
    write_csv(run_dir / "summary.csv", summaries)

    print(f"Saved: {run_dir / 'eval.csv'}")
    print(f"Saved: {run_dir / 'summary.csv'}")
    for summary in summaries:
        print(
            f"{summary['prompt_version']}: category {summary['category_correct']}/{summary['case_count']}, "
            f"priority {summary['priority_correct']}/{summary['case_count']}, "
            f"P1 misses {summary['critical_p1_miss_count']}"
        )


if __name__ == "__main__":
    main()
