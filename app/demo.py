"""Local dataset, report, and evaluation routes for the frontend."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAIError

from app.schemas import RunSelection
from app.services import run_reports
from week2.exercise.run_eval import evaluate_run

router = APIRouter(prefix="/demo", tags=["Local demo"])


@router.get("/config")
def get_configuration():
    return run_reports.configuration()


@router.get("/datasets")
def get_datasets():
    return [{"id": key, "label": value["label"], "count": len(run_reports.dataset_cases(key)[2])}
            for key, value in run_reports.DATASETS.items()]


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str):
    try:
        _, _, cases = run_reports.dataset_cases(dataset_id)
        return run_reports.public_cases(cases)
    except ValueError as error:
        raise HTTPException(404, str(error)) from None


@router.post("/runs", status_code=201)
def create_run(selection: RunSelection):
    try:
        return run_reports.start_run(selection.dataset, selection.case_id)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None


@router.get("/runs")
def get_runs():
    return run_reports.list_runs()


@router.get("/runs/{run_id}")
def get_results(run_id: str):
    try:
        return run_reports.run_results(run_id)
    except (ValueError, OSError):
        raise HTTPException(404, "Run not found.") from None


@router.post("/runs/{run_id}/evaluate")
def evaluate_saved_run(run_id: str):
    try:
        evaluate_run(run_reports.run_directory(run_id), live=True)
        return run_reports.run_results(run_id)
    except OpenAIError:
        raise HTTPException(503, "Model client could not be configured. Check local credentials privately.") from None
    except (OSError, KeyError):
        raise HTTPException(404, "Could not read this run's predictions or judge metadata.") from None
    except ValueError as error:
        raise HTTPException(409, str(error)) from None


@router.get("/runs/{run_id}/files/{filename}")
def download_report(run_id: str, filename: str):
    if filename not in {"predictions.json", "judge_results.json", "eval.csv", "summary.csv"}:
        raise HTTPException(404, "Report file not found.")
    try:
        path = run_reports.run_directory(run_id) / filename
        if not path.is_file():
            raise ValueError("Missing report.")
    except ValueError:
        raise HTTPException(404, "Report file not found.") from None
    return FileResponse(path, filename=filename)
