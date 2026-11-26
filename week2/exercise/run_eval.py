"""Judge a saved run with --live; reuse saved judgments and write CSV reports."""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from openai import APIError, APIStatusError, OpenAIError

from app.schemas import MeetingAnalysis
from app.services.llm import MAX_OUTPUT_TOKENS, MAX_RETRIES, REASONING_EFFORT, REQUEST_TIMEOUT, create_client
from week2.exercise.evaluate import (
    MeetingJudgment, comparison_rows, evaluate_predictions, index_records, summary_row, validate_judgment,
)
from week2.exercise.run_cases import DATASET_PATH, REPORTS_DIR, load_run_cases

JUDGE_PROMPT_PATH = Path(__file__).with_name("judge_prompt.md")
SCORING_VERSION = "meeting-f1-v1"


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def new_report(run: dict, predictions_bytes: bytes, dataset_bytes: bytes, prompt: str) -> dict:
    metadata = {
        "predictions_sha256": hashlib.sha256(predictions_bytes).hexdigest(),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "scoring_version": SCORING_VERSION,
        "extractor": {name: run.get(name) for name in ["model", "prompt", "schema", "settings", "versions", "case_ids"]},
        "judge": {
            "model": run["model"], "prompt": prompt, "schema": MeetingJudgment.model_json_schema(),
            "settings": {"reasoning_effort": REASONING_EFFORT, "max_output_tokens": MAX_OUTPUT_TOKENS,
                         "timeout_seconds": REQUEST_TIMEOUT, "max_retries": MAX_RETRIES, "store": False},
            "versions": {name: version(name) for name in ["openai", "pydantic", "httpx"]},
        },
    }
    return {"metadata": metadata, "judgments": []}


def pending_cases(cases: list[dict], run: dict, report: dict) -> list[dict]:
    allowed = {case["id"] for case in cases}
    predictions = index_records(run["predictions"], "case_id", allowed)
    judgments = index_records(report["judgments"], "case_id", allowed)
    pending = []
    for case in cases:
        prediction = predictions.get(case["id"], {})
        if prediction.get("status") != "ok":
            continue
        try:
            analysis = MeetingAnalysis.model_validate(prediction["analysis"]).model_dump()
        except ValueError:
            raise ValueError(f"Invalid saved prediction: {case['id']}") from None
        record = judgments.get(case["id"], {})
        if record.get("status") == "ok":
            try:
                validate_judgment(case, analysis, record["judgment"])
                continue
            except (ValueError, KeyError):
                pass
        pending.append(case)
    return pending


def request_judgment(client, case: dict, analysis: dict, config: dict):
    return client.responses.create(
        model=config["model"],
        input=[
            {"role": "developer", "content": config["prompt"]},
            {"role": "user", "content": json.dumps({
                "meeting_text": case["input"], "expected": case["expected"], "predicted": analysis,
            }, ensure_ascii=False)},
        ],
        text={"format": {"type": "json_schema", "name": "meeting_judgment",
                         "schema": config["schema"], "strict": True}},
        reasoning={"effort": config["settings"]["reasoning_effort"]},
        max_output_tokens=config["settings"]["max_output_tokens"], store=False,
    )


def collect_judgments(client, cases: list[dict], run: dict, report: dict, report_path: Path) -> None:
    predictions = {record["case_id"]: record for record in run["predictions"]}
    for case in pending_cases(cases, run, report):
        record = {"case_id": case["id"], "status": "judge_error", "judgment": None,
                  "error": "", "created_at_utc": datetime.now(timezone.utc).isoformat()}
        try:
            response = request_judgment(client, case, predictions[case["id"]]["analysis"], report["metadata"]["judge"])
            record.update({"response_id": response.id, "model": response.model,
                           "response_status": response.status, "raw_output": response.output_text,
                           "usage": response.usage.model_dump() if response.usage else None})
            if response.status != "completed" or any(
                part.type == "refusal" for item in response.output if item.type == "message" for part in item.content
            ):
                raise ValueError("Incomplete or refused judgment.")
            parsed = MeetingJudgment.model_validate_json(response.output_text).model_dump()
            record["judgment"] = validate_judgment(case, predictions[case["id"]]["analysis"], parsed)
            record["status"] = "ok"
        except APIError as error:
            record["error"] = type(error).__name__
            if isinstance(error, APIStatusError):
                record["upstream_status"] = error.status_code
        except ValueError:
            record["error"] = "Invalid, incomplete, or refused judgment."
        report["judgments"] = [old for old in report["judgments"] if old["case_id"] != case["id"]]
        report["judgments"].append(record)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{case['id']}: {record['status']}")


def configuration_key(report: dict) -> str:
    config = {key: value for key, value in report["metadata"].items() if key != "predictions_sha256"}
    return fingerprint(config)


def write_reports(run_dir: Path, cases: list[dict], run: dict, report: dict) -> dict:
    rows, summary = evaluate_predictions(cases, run, report["judgments"])
    summary = {"run": run_dir.name, "configuration": configuration_key(report),
               "model": report["metadata"]["judge"]["model"], **summary,
               "predictions_sha256": report["metadata"]["predictions_sha256"],
               "judgments_sha256": fingerprint(report["judgments"])}
    comparisons = comparison_rows(cases, run, report["judgments"], rows)
    report["evaluation"] = summary
    (run_dir / "judge_results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(run_dir / "eval.csv", comparisons)
    write_csv(run_dir / "summary.csv", [summary_row(summary)])
    return summary


def evaluate_run(run_dir: Path, live: bool = False) -> dict:
    """Evaluate one saved run; shared by the terminal and frontend route."""
    predictions_bytes = (run_dir / "predictions.json").read_bytes()
    run = json.loads(predictions_bytes)
    dataset_bytes, cases = load_run_cases(run, DATASET_PATH)
    if run["dataset_sha256"] != hashlib.sha256(dataset_bytes).hexdigest():
        raise ValueError("Dataset differs from the saved extraction run.")
    print(f"Evaluating {len(cases)} case(s): {' '.join(case['id'] for case in cases)}")
    report = new_report(run, predictions_bytes, dataset_bytes, JUDGE_PROMPT_PATH.read_text(encoding="utf-8"))
    report_path = run_dir / "judge_results.json"
    if report_path.exists():
        saved = json.loads(report_path.read_text(encoding="utf-8"))
        if saved["metadata"] != report["metadata"]:
            raise ValueError("Saved judgments use different predictions/settings/prompt. Use a new run folder.")
        report = saved
    # Validate saved data before creating a provider client.
    evaluate_predictions(cases, run, report["judgments"])
    pending = pending_cases(cases, run, report)
    if pending and not live:
        raise ValueError(f"{len(pending)} judgments need paid requests. No calls made; use --live when authorized.")
    if pending:
        with create_client() as client:
            collect_judgments(client, cases, run, report, report_path)
    return write_reports(run_dir, cases, run, report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, nargs="?")
    parser.add_argument("--live", action="store_true", help="Allow paid judge requests for missing/failed judgments.")
    args = parser.parse_args()
    run_dir = args.run_dir or REPORTS_DIR / input("Run folder inside week2/reports: ").strip()
    try:
        summary = evaluate_run(run_dir, live=args.live)
    except OpenAIError:
        parser.error("Model client could not be configured. Check local credentials privately.")
    except (OSError, KeyError):
        parser.error("Could not read this run's predictions or judge metadata. Check saved files.")
    except ValueError as error:
        parser.error(str(error))
    print(f"Saved eval.csv and summary.csv: {summary['evaluation_status']}")
    if summary["f1"] is not None:
        print(f"Extraction F1: {summary['f1']:.2%} (model-judged)")
    else:
        print("No final extraction score: unresolved judge errors or no applicable items.")
    if summary["evaluation_status"] == "incomplete":
        parser.exit(1, "Evaluation incomplete. Errors saved; resume failed judgments with --live when authorized.\n")


if __name__ == "__main__":
    main()
