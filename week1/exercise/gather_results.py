"""Combine selected run summaries and calculate mean percentages. No model calls."""

import csv

from run_eval import REPORTS_DIR, write_csv


def gather_results(run_names: list[str]) -> tuple[list[dict], list[dict]]:
    if not run_names or len(run_names) != len(set(run_names)):
        raise ValueError("Choose at least one run folder, with no duplicates.")

    results = []
    by_version = {}
    for run_name in run_names:
        summary_path = REPORTS_DIR / run_name / "summary.csv"
        # The with block closes the file after we finish reading it.
        with summary_path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                row["run"] = run_name
                results.append(row)
                version = row["prompt_version"]
                if version not in by_version:
                    by_version[version] = []
                by_version[version].append(row)

    averages = []
    for version, rows in by_version.items():
        case_count = int(rows[0]["case_count"])
        category_total = 0.0
        priority_total = 0.0
        schema_total = 0.0
        p1_misses = 0
        failed_cases = 0

        for row in rows:
            if int(row["case_count"]) != case_count:
                raise ValueError("Choose runs with the same number of cases.")
            category_total += float(row["category_accuracy"])
            priority_total += float(row["priority_accuracy"])
            schema_total += float(row["schema_valid_rate"])
            p1_misses += int(row["critical_p1_miss_count"])
            failed_cases += int(row["failed_cases"])

        run_count = len(rows)
        averages.append({
            "prompt_version": version,
            "runs": run_count,
            "cases_per_run": case_count,
            "average_category_percentage": round(category_total / run_count * 100, 2),
            "average_priority_percentage": round(priority_total / run_count * 100, 2),
            "average_schema_valid_percentage": round(schema_total / run_count * 100, 2),
            "total_critical_p1_misses": p1_misses,
            "total_failed_cases": failed_cases,
        })

    return results, averages


def main() -> None:
    run_names = input("Run folders inside week1/reports (separated by spaces): ").split()
    results, averages = gather_results(run_names)
    write_csv(REPORTS_DIR / "ten_run_results.csv", results)
    write_csv(REPORTS_DIR / "averages.csv", averages)
    print(f"Saved: {REPORTS_DIR / 'ten_run_results.csv'}")
    print(f"Saved: {REPORTS_DIR / 'averages.csv'}")


if __name__ == "__main__":
    main()
