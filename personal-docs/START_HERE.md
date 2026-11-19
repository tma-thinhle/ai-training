# Start here

Your next goal is a working local starter and a small Week 1 experiment.

## What the first assignment actually does

Build a Python script that sends a fictional issue description to an AI model
and receives a category, priority, and suggested next actions as validated JSON.

Run three versions of your instructions (prompts) against the same 20 cases.
Record the results and explain the mistakes. This exercise needs no database,
document search, Jira integration, website, or cloud deployment.

Read course slides 22-23 for the assignment and implementation hints. The
course's initial setup checklist is on slides 18-19.

## What is already ready

Checked on 2026-11-10:

- Python 3.13.0 and Git are available in this terminal.
- `python scripts/smoke_test.py`: PASS; all expected fixture counts match.
- `python -m pytest -q`: 3 passed. Pytest reported two local cache-write
  permission warnings; the API tests themselves passed.
- `AGENTS.md`, `.gitignore`, `.env.example`, and the database Compose file exist.
- This folder is not yet a Git repository.
- No project `.venv` was present during this check. Tests used the existing
  Python installation; this is not proof of a fresh isolated installation.
- Docker and GitHub CLI were not found on this terminal's PATH. That alone
  does not establish whether they are installed elsewhere.

## Do these in order

1. Obtain the course Git repository and approved model access from the AI Lead
   (slides 18-19). If using your own repository, agree its visibility and review
   process. Public publishing is not a course requirement in the supplied deck.
2. Create an isolated Python environment in `.venv`, install the supplied
   requirements, and repeat the smoke check and tests using that environment.
3. Supply the approved API key locally through environment variables or `.env`.
   `.env.example` documents variable names and placeholders; it holds no real key.
   Keep real keys out of Git, screenshots, logs, and browser-side code.
4. Complete the assigned Week 1 learning from slide 22. Explain what a prompt,
   JSON output, and output validation mean before building the experiment.
5. Make one model call for one synthetic issue and inspect the result.
6. Build up to three prompt versions and the same 20-case comparison. Use the
   existing human-defined reference labels; never change them to improve scores.
7. Submit one weekly PR with run instructions, results, sample input/output,
   mistakes, and a short demo. Follow `evidence/weekly_pr_template.md`.

The deck lists Docker among initial tools. The Week 1 classifier itself does not
use a database or container. Schedule the Docker setup as part of onboarding;
the supplied pgvector database first supports the Week 3 assignment.

## Week 1 success checklist

Source: course slides 22-23.

- [ ] Classify issues as Bug, Feature, Question, or Risk.
- [ ] Return P1/P2/P3 priority and suggested next actions.
- [ ] Save prompt versions V1, V2, and V3.
- [ ] Validate outputs against the agreed JSON schema.
- [ ] Evaluate the same 20 labelled cases for each version.
- [ ] Reach at least 85% category accuracy (17 out of 20).
- [ ] Have all successful outputs conform to the agreed schema.
- [ ] Detect all critical test incidents as P1.
- [ ] Explain prompt changes and observed errors honestly; do not invent results.
- [ ] Submit prompts, case reference, evaluation CSV, and a five-minute demo.

The supplied scorer measures category accuracy, priority accuracy, and critical
P1 misses. Schema validation and next-action quality need separate verification.

## Keep organization simple

- Preserve the supplied `app/`, `scripts/`, `tests/`, and `data/` paths.
- Use one repository for the program and one branch/PR for each weekly submission.
- Keep weekly evidence under `evidence/w01/`, `evidence/w02/`, and so on when needed.
- Use the existing `week1/` folder for the standalone W1 lab if desired; there is
  no need to duplicate the entire starter for every week.
- Keep later reusable application code in `app/`; the deck suggests this for W2.
- Use `evidence/weekly_tracker.md` as an index to PRs, evidence, and mentor feedback.
- Keep personal learning notes here in `personal-docs/`.

## Model access decision

First preference: the company-approved access and budget specified by the AI Lead.
The reference course stack uses OpenAI, including its SDK and later agent tools.

If free access is necessary, Gemini's API has a free tier for selected models,
subject to eligibility and usage limits. Ask whether an alternative provider is
accepted before adapting course code; it is not automatically a drop-in replacement.
Use synthetic fixtures only. Google's free-tier pricing page also states that
content may be used to improve its products.

Official pricing checked on 2026-11-10:
https://ai.google.dev/gemini-api/docs/pricing

Do not install a local model or add multiple providers just to begin Week 1.
One accepted model endpoint is enough for the first experiment.

## Questions for the AI Lead

- Which repository should I use, and is public publishing permitted?
- Which model/API access and budget are provided? Is a free Gemini alternative accepted?
- What is my current assignment deadline? The deck's printed schedule starts
  on 2026-10-19; it may not match my personal start date.

## Later assignments in ordinary language

| Week | What you build |
| --- | --- |
| 1 | Label issue descriptions and compare three prompts. |
| 2 | Turn meeting notes into a structured summary through an API. |
| 3 | Search the supplied project documents by meaning. |
| 4 | Answer questions using those search results and cite the sources. |
| 5 | Read fake Jira tasks and explain blockers and overdue work. |
| 6 | Combine documents and tasks into a report for human review. |
| 7 | Secure, test, monitor, and deploy the combined application. |
| 8 | Demonstrate it and explain your own work. |

Source: `slide-deck/course_slides.md`. The source slide deck remains authoritative.
