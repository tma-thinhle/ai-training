"""Check our output rules using invented JSON; no model calls or gold cases."""

import json

import pytest
from pydantic import ValidationError

from week1.exercise.schema import validate_classification


def test_valid_classification_is_accepted():
    output_text = '{"category":"Feature","priority":"P3","next_actions":["Confirm the shortcut."]}'

    classification = validate_classification(output_text)

    assert classification.category == "Feature"
    assert classification.priority == "P3"
    assert classification.next_actions == ["Confirm the shortcut."]


def test_malformed_json_is_rejected():
    with pytest.raises(ValidationError):
        validate_classification("This is not JSON.")


def test_unknown_category_is_rejected():
    output_text = '{"category":"Task","priority":"P3","next_actions":["Review the issue."]}'

    with pytest.raises(ValidationError, match="category"):
        validate_classification(output_text)


def test_unknown_priority_is_rejected():
    output_text = '{"category":"Feature","priority":"urgent","next_actions":["Review the issue."]}'

    with pytest.raises(ValidationError, match="priority"):
        validate_classification(output_text)


def test_missing_field_is_rejected():
    output_text = '{"category":"Feature","next_actions":["Review the issue."]}'

    with pytest.raises(ValidationError, match="priority"):
        validate_classification(output_text)


def test_extra_field_is_rejected():
    output_text = '{"category":"Feature","priority":"P3","next_actions":["Review the issue."],"confidence":0.9}'

    with pytest.raises(ValidationError, match="confidence"):
        validate_classification(output_text)


def test_invalid_actions_are_rejected():
    for actions in [[], [""], ["   "], [123], "Review the issue."]:
        output_text = json.dumps({
            "category": "Feature",
            "priority": "P3",
            "next_actions": actions,
        })

        # Pydantic's ValidationError and our blank-text error are both ValueErrors.
        with pytest.raises(ValueError):
            validate_classification(output_text)


def test_validated_data_can_be_written_as_json():
    output_text = '{"category":"Question","priority":"P3","next_actions":["Check the documentation."]}'
    classification = validate_classification(output_text)

    printed_json = classification.model_dump_json(indent=2)

    assert json.loads(printed_json) == json.loads(output_text)
