"""Collect predictions through the running FastAPI endpoint, never OpenAI directly."""

import argparse

import httpx

# Keep these imports available to the unchanged evaluation scripts.
from app.services.run_reports import DATASET_PATH, PROJECT_ROOT, REPORTS_DIR, load_run_cases, select_cases

API_URL = "http://127.0.0.1:8002"


def collect_predictions(client, cases: list[dict], run: dict) -> None:
    for case in cases:
        # Only meeting text is sent; golden answers never enter extraction requests.
        response = client.post(
            "/analyze-meeting",
            json={"meeting_text": case["input"]},
            headers={"X-Run-ID": run["run_id"], "X-Case-ID": case["id"]},
        )
        print(f"{case['id']}: HTTP {response.status_code}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow paid extraction through the API.")
    parser.add_argument("--case-id", help="Collect just one case ID from the selected dataset.")
    parser.add_argument("--dataset", choices=["original", "long"], default="original")
    parser.add_argument("--api-url", default=API_URL)
    args = parser.parse_args()
    if not args.live:
        parser.error("No requests sent. --live is required for paid model calls.")

    try:
        # The server owns model timeouts/retries. Do not retry HTTP POSTs here.
        with httpx.Client(base_url=args.api_url, timeout=None, trust_env=False) as client:
            response = client.post("/demo/runs", json={"dataset": args.dataset, "case_id": args.case_id})
            if response.status_code != 201:
                parser.error(f"Cannot start run: HTTP {response.status_code}. Check dataset/case selection.")
            run = response.json()
            print(f"Run folder: {run['run_id']}")
            collect_predictions(client, run["cases"], run)
    except httpx.RequestError:
        parser.error("Cannot reach the API. Start FastAPI and check --api-url.")
    print(f"Saved by the API: {run['report_path']}")
    print(f"Evaluate later (paid): {run['eval_command']}")


if __name__ == "__main__":
    main()
