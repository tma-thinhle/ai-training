"""Week 2 meeting-notes API. The starter Jira mock remains a separate app."""

from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import APIError, APIStatusError, APITimeoutError, OpenAI, OpenAIError, RateLimitError

from app.schemas import InvalidRequest, MeetingAnalysis, MeetingRequest
from app.services.llm import PROMPT_PATH, create_client, request_analysis, validate_model_response
from app.demo import router as demo_router
from app.services import run_reports

app = FastAPI(title="Meeting Notes API", version="0.1", responses={422: {"model": InvalidRequest}})
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{host}:{port}" for host in ["localhost", "127.0.0.1"] for port in [5500, 5501]],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Run-ID", "X-Case-ID"],
)
app.include_router(demo_router)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, error: RequestValidationError) -> JSONResponse:
    messages = {
        "missing": "{field} is required.",
        "extra_forbidden": "Remove unexpected field: {field}.",
        "string_type": "{field} must be text.",
        "string_too_short": "{field} must contain text, not just spaces.",
        "string_pattern_mismatch": "{field} must contain text, not just spaces.",
        "json_invalid": "Send valid JSON, with field names and text in double quotes.",
        "model_attributes_type": "Request body must be a JSON object.",
        "model_type": "Request body must be a JSON object.",
    }
    errors = []
    for item in error.errors():
        field = ".".join(str(part) for part in item["loc"][1:]) or "Request body"
        template = messages.get(item["type"])
        message = template.format(field=field) if template else f"{field}: {item['msg']}"
        # FastAPI may report the same field through multiple dependencies.
        if message not in errors:
            errors.append(message)
    return JSONResponse(status_code=422, content={"detail": "Invalid request body.", "errors": errors})


def get_run_context(request: MeetingRequest, http_request: Request) -> dict | None:
    run_id = http_request.headers.get("X-Run-ID")
    case_id = http_request.headers.get("X-Case-ID")
    if not run_id and not case_id:
        return None
    if not run_id or not case_id:
        raise HTTPException(400, "Both run ID and case ID are required.")
    try:
        run = run_reports.read_run(run_id)
        run_reports.check_run_case(run, case_id, request.meeting_text)
    except (ValueError, OSError):
        raise HTTPException(409, "Run or case is invalid; start a new run with unchanged source and settings.") from None
    return {"run": run, "case_id": case_id}


def get_client(context: dict | None = Depends(get_run_context)) -> Iterator[OpenAI]:
    try:
        client = create_client()
    except OpenAIError:
        run_reports.save_prediction(context, {"status": "api_error", "analysis": None,
                                             "http_status": 503, "error": "Model service is not configured."})
        raise HTTPException(503, "Model service is not configured.") from None
    with client:
        yield client


@app.post(
    "/analyze-meeting",
    response_model=MeetingAnalysis,
    responses={
        502: {"description": "Upstream failure or invalid model response"},
        503: {"description": "Model rate limit or missing configuration"},
        504: {"description": "Model timeout"},
    },
)
def analyze_meeting(request: MeetingRequest, client: OpenAI = Depends(get_client),
                    context: dict | None = Depends(get_run_context)) -> MeetingAnalysis:
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    prediction = {"status": "api_error", "analysis": None, "error": ""}
    try:
        response = request_analysis(client, request.meeting_text, prompt_text)
        prediction["response_status"] = response.status
        if context is not None:
            prediction.update({"response_id": response.id, "model": response.model,
                               "response_status": response.status, "raw_output": response.output_text,
                               "usage": response.usage.model_dump() if response.usage else None})
        result = validate_model_response(response)
        prediction.update(status="ok", analysis=result.model_dump(), http_status=200)
        run_reports.save_prediction(context, prediction)
        return result
    except APITimeoutError:
        prediction.update(error="APITimeoutError", http_status=504)
        run_reports.save_prediction(context, prediction)
        return JSONResponse(status_code=504, content={"detail": "Model service timed out.", "error_type": "timeout"})
    except RateLimitError:
        prediction.update(error="RateLimitError", http_status=503, upstream_status=429)
        run_reports.save_prediction(context, prediction)
        return JSONResponse(status_code=503, content={"detail": "Model service is rate limited; try again later.",
                                                     "error_type": "rate_limit", "upstream_status": 429})
    except APIError as error:
        prediction.update(error=type(error).__name__, http_status=502)
        if isinstance(error, APIStatusError):
            prediction["upstream_status"] = error.status_code
        run_reports.save_prediction(context, prediction)
        detail = "Model service request failed."
        if prediction.get("upstream_status") in {400, 401, 403, 404}:
            detail = "Model service rejected the request. Check the model and API key permissions."
        return JSONResponse(status_code=502, content={"detail": detail, "error_type": type(error).__name__,
                                                     "upstream_status": prediction.get("upstream_status")})
    except ValueError:
        status = "response_error" if prediction.get("response_status", "completed") != "completed" else "invalid_output"
        prediction.update(status=status, error="Invalid, refused, or malformed model response.", http_status=502)
        run_reports.save_prediction(context, prediction)
        return JSONResponse(status_code=502, content={"detail": "Model service returned an invalid or incomplete response.",
                                                     "error_type": status})
