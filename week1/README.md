# Week 1: Issue Classification

Build a standalone classifier and understand its behavior: issue text -> model response -> validated result -> evaluation.

## Start or resume

1. Read [our learning workflow](study/LEARNING_WORKFLOW.md).
2. Check [current progress and the next step](study/progress.md).
3. Follow the [study reading order](study/README.md).

## Organization

- `exercise/`: implementation, prompts, tests, and actual evaluation results; created as needed.
- `study/`: lessons, references, and resume notes.
- `demo/`: demonstration materials; created when useful.

## Course requirements

Source: [course slides 16 and 22-23](../slide-deck/course_slides.md#slide-22).

- Classify as Bug, Feature, Question, or Risk; assign P1/P2/P3 and suggest next actions.
- Validate responses against an agreed output schema.
- Compare V1, V2, and V3 on the same 20 supplied human-labelled cases.
- Target at least 17/20 category accuracy, schema compliance for every successful output, and zero critical P1 misses.
- Explain prompt changes and measured effects. The deck expects V3 to improve on V1; report any unmet expectation honestly.
- Submit prompts, the case reference, evaluation CSV, and a five-minute demo using the supplied weekly submission template.

The exact schema and detailed category/priority policy need documenting as implementation decisions. The supplied scorer does not assess schema validity or next-action quality. Failed cases stay visible; the 20 cases remain the evaluation denominator.

## Current status

The initial lesson is available. No classifier or model evaluation has been implemented or run. Run instructions will be added alongside working code.
