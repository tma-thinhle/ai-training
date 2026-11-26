"""Define and check the JSON returned by our issue classifier."""

from typing import Literal

from pydantic import BaseModel, Field


class IssueClassification(BaseModel): # inherits Pydantic base model
    model_config = {"extra": "forbid", "strict": True}

    category: Literal["Bug", "Feature", "Question", "Risk"]
    priority: Literal["P1", "P2", "P3"]
    next_actions: list[str] = Field(min_length=1)


def validate_classification(output_text: str) -> IssueClassification:
    classification = IssueClassification.model_validate_json(output_text)

    for action in classification.next_actions:
        if not action.strip(): # no allowing empty items here
            raise ValueError("Each next action must contain text.")

    return classification
