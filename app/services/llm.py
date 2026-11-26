"""Request structured meeting extraction and validate the response locally."""

from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import Response

from app.schemas import MeetingAnalysis, validate_analysis

MODEL = "gpt-6-luna"
REASONING_EFFORT = "low"
MAX_OUTPUT_TOKENS = 1500
REQUEST_TIMEOUT = 30
MAX_RETRIES = 1
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = Path(__file__).with_name("meeting_prompt.md")


def create_client() -> OpenAI:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    return OpenAI(timeout=REQUEST_TIMEOUT, max_retries=MAX_RETRIES)


def request_analysis(client: OpenAI, meeting_text: str, prompt_text: str) -> Response:
    return client.responses.create(
        model=MODEL,
        input=[
            {"role": "developer", "content": prompt_text},
            {"role": "user", "content": meeting_text},
        ],
        text={"format": {
            "type": "json_schema",
            "name": "meeting_analysis",
            "schema": MeetingAnalysis.model_json_schema(),
            "strict": True,
        }}, 
        reasoning={"effort": REASONING_EFFORT},
        max_output_tokens=MAX_OUTPUT_TOKENS,
        store=False,
    )


def validate_model_response(response: Response) -> MeetingAnalysis:
    if response.status != "completed":
        raise ValueError("Model response did not complete.")
    for item in response.output:
        if item.type == "message":
            for part in item.content:
                if part.type == "refusal":
                    raise ValueError("Model declined extraction.")
    return validate_analysis(response.output_text)
