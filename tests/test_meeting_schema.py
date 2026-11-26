"""Check the contract with invented examples; no model calls."""

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.schemas import MeetingAnalysis, MeetingRequest, validate_analysis


def sample_analysis() -> dict:
    return {
        "summary": "Nira will update the checkout tests; no deadline was set.",
        "decisions": [],
        "actions": [{"owner": "Nira", "action": "Update checkout tests", "due_date": None}],
    }


def test_valid_request_preserves_meeting_text():
    request = MeetingRequest(meeting_text="Nira will update the checkout tests.")
    assert request.meeting_text == "Nira will update the checkout tests."


@pytest.mark.parametrize("payload", [
    {}, {"meeting_text": ""}, {"meeting_text": " \n "},
    {"meeting_text": None}, {"meeting_text": 123},
    {"meeting_text": "Notes", "unexpected": True},
])
def test_invalid_request_is_rejected(payload):
    with pytest.raises(ValidationError):
        MeetingRequest.model_validate(payload)


def test_missing_information_is_explicit_null():
    output = sample_analysis()
    output["actions"][0]["owner"] = None
    result = validate_analysis(json.dumps(output))
    assert result.actions[0].owner is None
    assert result.actions[0].due_date is None
    assert json.loads(result.model_dump_json()) == output


def test_no_decisions_or_actions_is_valid():
    result = MeetingAnalysis(summary="The meeting was cancelled.", decisions=[], actions=[])
    assert result.decisions == [] and result.actions == []


@pytest.mark.parametrize("field", ["owner", "action", "due_date"])
def test_action_fields_must_be_present_even_when_nullable(field):
    output = sample_analysis()
    del output["actions"][0][field]
    with pytest.raises(ValidationError):
        validate_analysis(json.dumps(output))


@pytest.mark.parametrize("due_date", [
    "tomorrow", "2026-2-03", "2026-02-30", "2026-13-01", "2026-11-25T00:00:00", "",
])
def test_invalid_calendar_dates_are_rejected(due_date):
    output = sample_analysis()
    output["actions"][0]["due_date"] = due_date
    with pytest.raises(ValidationError):
        validate_analysis(json.dumps(output))


def test_valid_calendar_date_is_preserved():
    output = sample_analysis()
    output["actions"][0]["due_date"] = "2028-02-29"
    assert validate_analysis(json.dumps(output)).actions[0].due_date == "2028-02-29"


def test_malformed_json_and_wrong_field_types_are_rejected():
    with pytest.raises(ValidationError):
        validate_analysis("not JSON")
    for field, value in [("summary", 123), ("decisions", "Keep checkout"), ("actions", {})]:
        output = sample_analysis()
        output[field] = value
        with pytest.raises(ValidationError):
            validate_analysis(json.dumps(output))


def test_blank_descriptions_and_extra_fields_are_rejected():
    original = sample_analysis()
    invalid = []
    for field, value in [("summary", "  "), ("decisions", [" "]), ("extra", True)]:
        output = deepcopy(original)
        output[field] = value
        invalid.append(output)
    for field, value in [("owner", " "), ("action", " "), ("extra", True), ("owner", 123)]:
        output = deepcopy(original)
        output["actions"][0][field] = value
        invalid.append(output)
    for output in invalid:
        with pytest.raises(ValidationError):
            validate_analysis(json.dumps(output))


def test_schema_validation_does_not_prove_a_claim_is_supported():
    # Valid structure, but no meeting text is consulted by this validator.
    output = sample_analysis()
    output["actions"][0]["owner"] = "Someone never mentioned in the meeting"
    assert validate_analysis(json.dumps(output)).actions[0].owner == output["actions"][0]["owner"]
