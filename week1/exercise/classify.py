"""Send one synthetic issue to OpenAI and validate the JSON response."""

from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import Response

from schema import validate_classification

MODEL = "gpt-5.6-luna"
REASONING_EFFORT = "low"
MAX_OUTPUT_TOKENS = 1500
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 0
EXERCISE_DIR = Path(__file__).resolve().parent


def classify_issue(client: OpenAI, issue_text: str, prompt_text: str) -> Response:
    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "developer", "content": prompt_text},
            {"role": "user", "content": issue_text},
        ],
        reasoning={"effort": REASONING_EFFORT},
        max_output_tokens=MAX_OUTPUT_TOKENS,
        store=False,
    )

    return response


def main() -> None:
    load_dotenv(EXERCISE_DIR.parent.parent / ".env", override=True)
    prompt_version = input("Prompt version (v1/v2/v3): ").strip()
    prompt_path = EXERCISE_DIR / "prompts" / f"{prompt_version}.md"
    prompt_text = prompt_path.read_text(encoding="utf-8")

    print(f"Week 1 | Prompt {prompt_version} | Model: {MODEL}")
    issue_text = input("Issue description: ").strip()

    print("Sending one request...")
    with OpenAI(timeout=REQUEST_TIMEOUT, max_retries=MAX_RETRIES) as client:
        response = classify_issue(client, issue_text, prompt_text)
    print(response.output_text)
    classification = validate_classification(response.output_text)
    print("\nValidated classification:")
    print(classification.model_dump_json(indent=2)) # serialization: converting validated object back to JSON


if __name__ == "__main__":
    main()
