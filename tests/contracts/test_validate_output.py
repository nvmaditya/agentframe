"""validate_output coerces against an annotation and raises a structured error."""

from __future__ import annotations

from typing import Literal, Optional

import pytest
from pydantic import BaseModel, ValidationError

from agentframe.contracts import validate_output


class Ticket(BaseModel):
    kind: str
    id: int


def test_accepts_matching_primitive() -> None:
    assert validate_output(3, int) == 3


def test_coerces_compatible_values() -> None:
    assert validate_output("7", int) == 7


def test_rejects_wrong_type_with_pydantic_error() -> None:
    with pytest.raises(ValidationError) as exc:
        validate_output("nope", int)
    errors = exc.value.errors()
    assert errors
    assert "type" in errors[0] or "int_parsing" in errors[0]["type"]


def test_validates_pydantic_model_and_returns_instance() -> None:
    ticket = validate_output({"kind": "bug", "id": 1}, Ticket)
    assert isinstance(ticket, Ticket)
    assert ticket.kind == "bug"
    assert ticket.id == 1


def test_optional_none_passes() -> None:
    assert validate_output(None, Optional[int]) is None


def test_json_schema_object_validates_required_fields() -> None:
    schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }
    assert validate_output({"text": "hi"}, schema).text == "hi"
    with pytest.raises(ValidationError):
        validate_output({}, schema)


def test_literal_must_match() -> None:
    assert validate_output("on", Literal["on", "off"]) == "on"
    with pytest.raises(ValidationError):
        validate_output("maybe", Literal["on", "off"])
