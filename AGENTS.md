# Repository Guidelines

## Project Structure & Module Organization
This Python 3.11+ starter kit supports an eight-week AI Engineering training program. Preserve its role as reusable scaffolding. The course slide deck defines requirements and acceptance criteria.

- `app/mock_jira.py`: read-only FastAPI mock Jira service.
- `tests/`: pytest API tests.
- `scripts/`: fixture validation and issue-classifier scoring tools.
- `data/documents/`, `data/jira/`, `data/evaluation/`: synthetic corpus, issues, and evaluation fixtures.
- `assignments/`: weekly handoff instructions.
- `evidence/`: submission artifacts and `weekly_pr_template.md`.

## Build, Test, and Development Commands
Run commands from the repository root after creating and activating a virtual environment (`python -m venv .venv`).

- `pip install -r requirements.txt`: install dependencies.
- `python scripts/smoke_test.py`: validate fixture counts; output must end with `PASS`.
- `pytest -q`: run all tests; the starter contains three tests.
- `pytest -q tests/test_mock_jira.py::test_cross_project_denied`: run one test.
- `uvicorn app.mock_jira:app --reload --port 8001`: start the API; browse `/docs`.
- `docker compose up -d db`: start local PostgreSQL with pgvector for Week 3 onward.
- `python scripts/evaluate_issue_classifier.py evidence/w1_predictions.csv`: score predictions with CSV headers `issue_id,predicted_category,predicted_priority`.

There is no separate build step or configured formatter/linter.

## Coding Style & Naming Conventions
Use four-space indentation, `snake_case` for Python functions and modules, and uppercase names for constants. Match the compact style of surrounding code and retain type annotations where present. Name tests `test_<behavior>` in `tests/test_*.py`.

## Testing Guidelines
Use pytest and FastAPI's `TestClient`. Cover successful reads, denied cross-project access, and rejected writes when changing API behavior. Run the smoke check after fixture changes; its counts are exact. Never change training gold labels to make evaluations pass. No numeric coverage threshold is configured.

## Commit & Pull Request Guidelines
Git history is unavailable in this checkout; use concise, imperative commit subjects describing the change. Implement assignments on separate branches. Follow `evidence/weekly_pr_template.md`: include the feature, implementation summary, run instructions, test/evaluation results, known failures, demo link, and next action. Obtain AI Lead review for weekly submissions.

## Security & Configuration
Copy `.env.example` to `.env` and supply runtime credentials; never commit secrets. Use synthetic data only. Keep hidden mentor assessments outside this kit. Preserve the mock's read-only behavior; `X-Allowed-Project` is teaching authorization and must be replaced before production use.
