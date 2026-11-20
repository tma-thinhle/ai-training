"""Collect model predictions for the same cases using V1, V2, and V3."""

import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import APIError, APIStatusError, OpenAI

from classify import (
    MODEL, MAX_OUTPUT_TOKENS, MAX_RETRIES, REASONING_EFFORT,
    REQUEST_TIMEOUT, classify_issue,
)
from schema import validate_classification

EXERCISE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXERCISE_DIR.parent.parent
GOLD_PATH = PROJECT_ROOT / "data" / "evaluation" / "issue_classification_gold.json"
REPORTS_DIR = EXERCISE_DIR.parent / "reports"


def collect_predictions(client: OpenAI, cases: list[dict], run: dict, report_path: Path) -> None:
    for version, prompt_text in run["prompts"].items():
        for case in cases:
            prediction = {
                "prompt_version": version,
                "issue_id": case["issue_id"],
                "status": "pending",
                "raw_output": None,
                "classification": None,
                "error": "",
            }

            try:
                # Only issue text goes to the model. 
                response = classify_issue(client, case["text"], prompt_text)
                prediction["raw_output"] = response.output_text
                prediction["response_status"] = response.status
                prediction["response_id"] = response.id
                prediction["model"] = response.model
                prediction["usage"] = None
                if response.usage is not None:
                    prediction["usage"] = response.usage.model_dump()

                if response.status != "completed":
                    prediction["status"] = "response_error"
                    prediction["error"] = f"Response status: {response.status}"
                else:
                    classification = validate_classification(response.output_text)
                    prediction["classification"] = classification.model_dump()
                    prediction["status"] = "ok"
            except APIError as error:
                prediction["status"] = "api_error"
                prediction["error"] = type(error).__name__
                if isinstance(error, APIStatusError):
                    prediction["error"] += f" (HTTP {error.status_code})"
            except ValueError:
                prediction["status"] = "invalid_output"
                prediction["error"] = "JSON or schema validation failed."

            run["predictions"].append(prediction)
            # Save each attempt before starting the next case.
            report_path.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"{version} {case['issue_id']}: {prediction['status']}")


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    cases = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    created_at = datetime.now(timezone.utc)
    run_id = created_at.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = REPORTS_DIR / run_id
    run_dir.mkdir(parents=True)

    run = {
        "run_id": run_id,
        "created_at_utc": created_at.isoformat(),
        "dataset": str(GOLD_PATH.relative_to(PROJECT_ROOT)),
        "case_count": len(cases),
        "model": MODEL,
        "settings": {
            "reasoning_effort": REASONING_EFFORT,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "timeout_seconds": REQUEST_TIMEOUT,
            "max_retries": MAX_RETRIES,
            "store": False,
        },
        "prompts": {},
        "predictions": [],
    }
    for version in ["v3"]:
        prompt_path = EXERCISE_DIR / "prompts" / f"{version}.md"
        run["prompts"][version] = prompt_path.read_text(encoding="utf-8")

    print(f"Run folder: {run_id}")
    print(f"Collecting {len(cases)} cases.")
    with OpenAI(timeout=REQUEST_TIMEOUT, max_retries=MAX_RETRIES) as client:
        collect_predictions(client, cases, run, run_dir / "predictions.json")

    print(f"Saved: {run_dir / 'predictions.json'}")


if __name__ == "__main__":
    main()
