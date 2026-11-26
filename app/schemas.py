"""Define the meeting request and the model output we accept."""

from datetime import date

from pydantic import BaseModel, Field, field_validator


class InvalidRequest(BaseModel):
    detail: str
    errors: list[str]


class MeetingRequest(BaseModel):
    model_config = {"extra": "forbid", "strict": True}

    meeting_text: str = Field(min_length=1, pattern=r"\S")


class RunSelection(BaseModel):
    model_config = {"extra": "forbid", "strict": True}

    dataset: str = "original"
    case_id: str | None = None


class ActionItem(BaseModel):
    model_config = {"extra": "forbid", "strict": True}

    owner: str | None = Field(pattern=r"\S")
    action: str = Field(min_length=1, pattern=r"\S")
    due_date: str | None = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

    @field_validator("due_date")
    @classmethod
    def check_calendar_date(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value


class MeetingAnalysis(BaseModel):
    model_config = {"extra": "forbid", "strict": True}

    summary: str = Field(min_length=1, pattern=r"\S")
    decisions: list[str]
    actions: list[ActionItem]

    @field_validator("decisions")
    @classmethod
    def check_decisions(cls, decisions: list[str]) -> list[str]:
        if any(not decision.strip() for decision in decisions):
            raise ValueError("Each decision must contain text.")
        return decisions


def validate_analysis(output_text: str) -> MeetingAnalysis:
    return MeetingAnalysis.model_validate_json(output_text)
