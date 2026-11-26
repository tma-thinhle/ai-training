# Week 2: Meeting Notes API

Turn meeting notes into a summary, decisions, and actions with an owner and due date.
Use `null` for missing owners or dates. Do not invent facts or dates.

Run all commands from the repository root in PowerShell.

## Setup

If `.venv` is already ready, skip installation. For a fresh checkout:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set `OPENAI_API_KEY` in the root `.env` file or your environment. Keep the key out
of Git, logs, and reports. Unit tests do not need a key.

## Run the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002
```

Open [Swagger UI](http://127.0.0.1:8002/docs) or
[OpenAPI JSON](http://127.0.0.1:8002/openapi.json).
Opening docs makes no model calls. Sending valid notes makes a paid model call.

Send `POST /analyze-meeting` with:

```json
{"meeting_text": "Nira will update checkout tests. No deadline was set."}
```

The response has `summary`, `decisions`, and `actions`. Each action has `owner`,
`action`, and `due_date`. Missing or invalid input returns HTTP 422 with a short
message and an `errors` list. The Jira mock runs as a separate app.

## Run API unit tests (UTs)

Run only [test_meeting_api.py](../tests/test_meeting_api.py):

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_meeting_api.py
```

To run one test:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_meeting_api.py::test_success_returns_validated_json_and_requests_structured_output
```

The tests use fake model replies and errors. They need no running server, API key,
or paid calls. They check valid output, input validation, docs, missing settings,
and these five required error cases:

| Error case | API response |
| --- | --- |
| Invalid input | 422 |
| Model timeout | 504 |
| Provider 429 | 503 |
| Provider 500 | 502 |
| Invalid model output | 502 |

These tests check API behavior. They do not measure real extraction quality.

For a separate offline example with an invented reply:

```powershell
.\.venv\Scripts\python.exe -m week2.demo.offline
```

## Use the frontend

1. Start the API above.
2. Open [frontend/index.html](frontend/index.html) with VS Code Live Server.
3. Choose **Original 20** or **Long 5**, then one case or all cases. Click **Run**.
4. Click **Evaluate · paid** to check the saved answers. Use **Reports** to view
   results, filter differences, and download JSON or CSV files.

Run and Evaluate make paid model calls. Opening the page or reports does not.
Each dataset run gets its own folder under `week2/reports/`. Model settings and
instructions are shown for reading. Long 5 uses draft answers and is extra practice.

For your own notes, choose **Custom**. Use `meeting_text` as the Request field.
Custom requests do not save a run or support evaluation. Change the field to
`hello` to try a real 422 response.

Live Server must use `localhost` or `127.0.0.1` on port 5500 or 5501. The API uses
port 8002. For another API port, add `?api=http://127.0.0.1:8003` to the page URL.
There is no frontend install or build step.

The workspace [settings](../.vscode/settings.json) stop report writes from
reloading the page during a batch. Restart Live Server after changing them.

The UI marks errors seen in this browser session. The unit tests cover all five
required errors; you do not need real provider failures to run them. A rejected
model is not proof of a provider 500. See the [demo guide](demo/README.md) for more.

## Run from the terminal

Collect answers, evaluate one run, then combine runs if needed. Agents need your
explicit instruction before running paid steps.

### 1. Collect answers (paid)

Start the API, then run:

```powershell
.\.venv\Scripts\python.exe -m week2.exercise.run_cases --live
```

This sends the original 20 cases to `/analyze-meeting`. Only meeting text goes to
the model. The API saves answers, errors, model settings, prompts, usage, and the
dataset hash in `week2/reports/<run-id>/predictions.json`.

Options: `--case-id TC15` for one case, `--dataset long` for all five long cases,
or `--dataset long --case-id LC01` for one long case. Use `--api-url` to change
the API address. Each command creates a new run with only the selected cases.

### 2. Evaluate a run (paid for missing or failed checks)

Replace `<run-id>` with the folder name:

```powershell
.\.venv\Scripts\python.exe -m week2.exercise.run_eval week2/reports/<run-id> --live
```

A separate request to the same model checks each successful answer against the
notes and reference answer. Python checks the matches, owners, dates, and scores.
The UI Evaluate button uses the same code and saved checks.

The run folder contains:

| File | Contents |
| --- | --- |
| `predictions.json` | Saved answers, settings, and extraction errors |
| `judge_results.json` | Model checks, settings, and full scores |
| `eval.csv` | Reference and predicted answers, with reasons for differences |
| `summary.csv` | Counts, F1, summary issues, and errors for one run |

Completed checks are reused. Only missing or failed checks need more calls.
Leave out `--live` to rebuild CSVs when all needed checks are saved.
Changed answers, prompts, or settings cannot reuse old checks. The dataset must
still match the saved hash. To try different judge settings without extracting
again, copy `predictions.json` into a new folder and evaluate that folder.

Failed or missing extractions count expected items as missed. Failed judge checks
leave the final F1 blank; rerun with `--live` to retry them. Both model steps allow
one SDK retry per request, so a full run can use up to 40 attempts per step.

### 3. Combine runs (offline, optional)

```powershell
.\.venv\Scripts\python.exe -m week2.exercise.gather_results RUN_A RUN_B
```

Replace `RUN_A` and `RUN_B` with folders inside `week2/reports`. With no arguments,
the script asks for folder names. It writes `all_run_results.csv` and `results.csv`.

It adds correct, extra, and missed counts before calculating F1. Different
settings or case selections stay in separate groups. Duplicate copies or changed
source data are rejected. An incomplete group has no final score. Include poor
results too. Repeated runs use the same meetings, not new cases.

## Submission results

These are the evaluation reports used for the Week 2 submission:

- [all_run_results.csv](reports/all_run_results.csv): results for the selected run.
- [results.csv](reports/results.csv): overall results. This report contains one run.

The run, `final-run`, sent 20 extraction requests for the original 20 cases.
An AI judge checked the answers against the notes and reference answers.
The gather script collected the results:

```powershell
.\.venv\Scripts\python.exe -m week2.exercise.gather_results final-run
```

All 20 outputs follow the schema. The AI evaluation found 51 correct items,
0 extra items, and 1 missed item: **99.03% F1**. There were no extraction failures
or judge errors. Three summaries need review; summary quality is separate from F1.

Keep the [run files](reports/final-run/) with these reports so the reviewer can
check the saved answers, prompts, settings, and AI judgments. The score exceeds
our chosen 85% F1 target; mentor acceptance of the metric and Gate 1 review are pending.

## Evaluation rules

- Use the supplied 20 cases: 15 decisions and 37 actions, counting each owner.
- Our chosen target is combined decision/action F1 of at least 85%. Mentor
  acceptance of this metric is pending.
- Match text by meaning. Ignore order and whitespace. Each item can match once.
- Owners and dates must match exactly, including `null`. A shared task has one
  action per named owner.
- Correct = matched item. Extra = wrong or added item. Missed = unmatched reference
  item. A wrong owner or date counts as one extra and one missed item.
- Precision = correct / (correct + extra).
- Recall = correct / (correct + missed).
- F1 = 2 * correct / (2 * correct + extra + missed).
- A zero denominator leaves the score blank. CSV F1 is shown as a percentage.
- Summary quality, valid output, and errors are reported separately from F1.
  Passing F1 does not mean every summary is complete or 17/20 meetings are perfect.
- Scores come from a model judge and can contain mistakes. Public cases do not
  show how well the API handles unseen notes.

## Course criteria

See [slides 24-25](../slide-deck/course_slides.md#slide-24),
[Gate 1](../slide-deck/course_slides.md#slide-44), and the
[shared contract](../data/week2/week2_meeting_notes_expected_20_cases.md).

- Run the API from this README and open its docs.
- Make every successful response follow the JSON schema.
- Reach at least 85% fact/action extraction on the original 20 labelled cases.
- Pass all five error tests listed above.
- Check that Git, logs, and evidence contain no secrets.
- Submit a source PR, sample requests and responses, test results, evaluation
  results, and a screen recording. Use the [PR template](../evidence/weekly_pr_template.md).
- Explain the code, results, and limits. Obtain AI Lead review for Gate 1.

Saved reports provide evidence; they do not by themselves establish a gate pass.
See the [demo guide](demo/README.md) and [submission draft](demo/submission.md).
