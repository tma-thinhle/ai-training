"""Small JSON report helpers shared by the API and evaluation scripts."""

import csv
import hashlib
import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from app.schemas import MeetingAnalysis
from app.services import llm

PROJECT_ROOT = llm.PROJECT_ROOT
DATASET_PATH = PROJECT_ROOT / "data/week2/week2_meeting_notes_expected_20_cases.json"
REPORTS_DIR = PROJECT_ROOT / "week2/reports"
DATASETS = {
    "original": {"label": "Original 20 cases", "path": DATASET_PATH},
    "long": {"label": "Long 5 cases (draft references)",
             "path": PROJECT_ROOT / "data/week2/week2_meeting_notes_long_5_cases.json"},
}


def select_cases(cases: list[dict], case_ids: list[str] | None) -> list[dict]:
    if case_ids is None:
        return cases  # Older runs without a selection used the whole dataset.
    if (not isinstance(case_ids, list) or not case_ids
            or any(not isinstance(case_id, str) for case_id in case_ids)
            or len(case_ids) != len(set(case_ids))):
        raise ValueError("Selected case IDs must be a nonempty list without duplicates.")
    by_id = {case["id"]: case for case in cases}
    if any(case_id not in by_id for case_id in case_ids):
        raise ValueError("Unknown case ID; no requests sent.")
    return [by_id[case_id] for case_id in case_ids]


def load_run_cases(run: dict, default_path: Path) -> tuple[bytes, list[dict]]:
    dataset_path = default_path
    if run.get("dataset"):
        dataset_path = (PROJECT_ROOT / run["dataset"]).resolve()
        if not dataset_path.is_relative_to(PROJECT_ROOT):
            raise ValueError("The saved dataset must be inside the repository.")
    dataset_bytes = dataset_path.read_bytes()
    cases = select_cases(json.loads(dataset_bytes), run.get("case_ids"))
    return dataset_bytes, cases


def configuration() -> dict:
    return {
        "model": llm.MODEL,
        "settings": {"reasoning_effort": llm.REASONING_EFFORT, "max_output_tokens": llm.MAX_OUTPUT_TOKENS,
                     "timeout_seconds": llm.REQUEST_TIMEOUT, "max_retries": llm.MAX_RETRIES, "store": False},
        "prompt": llm.PROMPT_PATH.read_text(encoding="utf-8"),
        "schema": MeetingAnalysis.model_json_schema(),
        "versions": {name: version(name) for name in ["openai", "pydantic", "fastapi", "httpx"]},
    }


def dataset_cases(dataset: str) -> tuple[Path, bytes, list[dict]]:
    if dataset not in DATASETS:
        raise ValueError("Unknown dataset.")
    path = DATASETS[dataset]["path"]
    source = path.read_bytes()
    return path, source, json.loads(source)


def public_cases(cases: list[dict]) -> list[dict]:
    # Golden answers never appear in the extraction payload supplied to the UI/CLI.
    return [{"id": case["id"], "title": case.get("title", case["id"]), "input": case["input"]} for case in cases]


def run_directory(run_id: str) -> Path:
    path = (REPORTS_DIR / run_id).resolve()
    if not run_id or path.parent != REPORTS_DIR.resolve():
        raise ValueError("Invalid run folder.")
    return path


def read_run(run_id: str) -> dict:
    return json.loads((run_directory(run_id) / "predictions.json").read_text(encoding="utf-8"))


def write_run(run: dict) -> None:
    path = run_directory(run["run_id"]) / "predictions.json"
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")


def start_run(dataset: str, case_id: str | None) -> dict:
    path, source, cases = dataset_cases(dataset)
    cases = select_cases(cases, [case_id] if case_id is not None else None)
    created = datetime.now(timezone.utc)
    run_id = created.strftime("%Y%m%dT%H%M%S%fZ")
    run = {"run_id": run_id, "created_at_utc": created.isoformat(),
           "dataset": str(path.relative_to(PROJECT_ROOT)), "dataset_sha256": hashlib.sha256(source).hexdigest(),
           "case_ids": [case["id"] for case in cases], **configuration(),
           "transport": "http", "endpoint": "/analyze-meeting", "predictions": []}
    run_directory(run_id).mkdir(parents=True)
    write_run(run)
    return {"run_id": run_id, "cases": public_cases(cases), "case_ids": run["case_ids"],
            "model": run["model"], "settings": run["settings"], "prompt": run["prompt"],
            "report_path": f"week2/reports/{run_id}/predictions.json", "eval_command": evaluation_command(run_id)}


def evaluation_command(run_id: str) -> str:
    return rf".\.venv\Scripts\python.exe -m week2.exercise.run_eval week2/reports/{run_id} --live"


def check_run_case(run: dict, case_id: str, meeting_text: str) -> None:
    source, cases = load_run_cases(run, DATASET_PATH)
    if hashlib.sha256(source).hexdigest() != run["dataset_sha256"]:
        raise ValueError("Dataset changed; start a new run.")
    case = next((case for case in cases if case["id"] == case_id), None)
    if case is None or case["input"] != meeting_text:
        raise ValueError("Case ID or meeting text differs from this run.")
    if any(row["case_id"] == case_id for row in run["predictions"]):
        raise ValueError("This case already has a result; start a new run to repeat it.")
    current = configuration()
    if any(run[key] != current[key] for key in ["model", "settings", "prompt", "schema"]):
        raise ValueError("Model configuration changed; start a new run.")


def save_prediction(context: dict | None, prediction: dict) -> None:
    if context is not None:
        run = context["run"]
        run["predictions"].append({"case_id": context["case_id"], **prediction})
        write_run(run)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def list_runs() -> list[dict]:
    if not REPORTS_DIR.exists():
        return []
    rows = []
    for folder in REPORTS_DIR.iterdir():
        if folder.is_dir() and (folder / "predictions.json").exists():
            run = read_run(folder.name)
            rows.append({"run_id": folder.name, "created_at_utc": run.get("created_at_utc", ""),
                         "model": run["model"], "selected": len(run.get("case_ids", [])),
                         "completed": len(run["predictions"]), "evaluated": (folder / "summary.csv").exists()})
    return sorted(rows, key=lambda row: row["created_at_utc"], reverse=True)


def run_results(run_id: str) -> dict:
    run = read_run(run_id)
    folder = run_directory(run_id)
    summaries = read_csv(folder / "summary.csv")
    return {"run_id": run_id, "model": run["model"], "settings": run["settings"], "prompt": run["prompt"],
            "case_ids": run.get("case_ids", []), "predictions": run["predictions"],
            "summary": summaries[0] if summaries else None, "comparisons": read_csv(folder / "eval.csv"),
            "eval_command": evaluation_command(run_id),
            "files": [name for name in ["predictions.json", "judge_results.json", "eval.csv", "summary.csv"]
                      if (folder / name).exists()]}
