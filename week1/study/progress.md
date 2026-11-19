# Week 1 Progress

Updated: 2026-11-16 (Asia/Bangkok).

## Agreement and preferences

- Initial learning/build plan accepted: the learner said to start Week 1.
- Agent writes code, tests, and demos; learner studies explanations.
- Define terms before use; no required exercises or comprehension checkpoints.
- Keep weekly work in `week1/exercise/`, `week1/study/`, and `week1/demo/` as needed.
- Use OpenAI `gpt-5.6-luna`; account access remains unverified.
- Shared $10 balance across four people; no Week 1 spending allowance agreed. The proposed $0.50 allowance was not adopted.
- Git operations and cloud configuration remain outside scope.

## Material prepared

- Reusable learning workflow and Week 1 entry point.
- Lesson 01: model weights, training, tokens, inference, answer variability, prompts, and division of responsibilities.
- Lesson material is available for reading; learner understanding and external course completion have not been assessed.

## Environment and checks

- Python reports 3.13.0, meeting the course's 3.11+ requirement.
- No project `.venv` or `.env` found during this check.
- No dependencies installed or starter smoke/tests run in this increment.
- No assignment code implemented, API calls made, or evaluation scores produced.
- Teaching response in lesson 01 is explicitly illustrative.

## Decisions and open items

- User authorized removing the completed-assignment prohibition from root `AGENTS.md`; that edit was made earlier.
- Preserve supplied fixtures, human gold labels, tools, and mock API behavior.
- Document exact schema and priority/category policy before evaluation; course leaves details unspecified.
- Required output fields proposed so far: `category`, `priority`, `next_actions`.
- Record failures honestly; do not claim V3 improvement without evidence.
- API key must be configured locally; never request its value in chat.

## Exact next step

Create a project `.venv`, install supplied requirements, run fixture smoke and three starter tests, and explain what those checks prove. Resolve installation failures before assignment code (course slide 18). Then build the one-issue request increment, checking credential presence without exposing credentials. If access is unavailable, continue useful offline work and record the blocker.
