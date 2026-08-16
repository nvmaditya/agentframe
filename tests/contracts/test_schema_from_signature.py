"""schema_from_signature turns type hints into a JSON Schema object."""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional, Union

import pytest
from pydantic import BaseModel

from agentframe.contracts import schema_from_signature


class Kind(str, Enum):
    A = "a"
    B = "b"


class Payload(BaseModel):
    n: int
    label: str = "x"


def _plain(x: int, y: str) -> bool:
    return True


def _optional(x: Optional[int] = None) -> None:
    return None


def _union(x: Union[int, str]) -> int:
    return 0


def _literal(mode: Literal["on", "off"]) -> str:
    return mode


def _model(item: Payload) -> Payload:
    return item


def _enum(k: Kind) -> Kind:
    return k


class _HasSelf:
    def method(self, n: int) -> int:
        return n


def test_primitives_become_json_schema_properties() -> None:
    schema = schema_from_signature(_plain)
    assert schema["type"] == "object"
    assert schema["properties"]["x"]["type"] == "integer"
    assert schema["properties"]["y"]["type"] == "string"
    assert schema["required"] == ["x", "y"]


def test_self_is_omitted_from_schema() -> None:
    schema = schema_from_signature(_HasSelf.method)
    assert list(schema["properties"]) == ["n"]
    assert schema["required"] == ["n"]


def test_optional_parameter_is_not_required() -> None:
    schema = schema_from_signature(_optional)
    assert "x" in schema["properties"]
    assert "x" not in schema.get("required", [])


def test_union_and_literal_and_enum_and_model() -> None:
    union = schema_from_signature(_union)["properties"]["x"]
    assert "anyOf" in union or "oneOf" in union or union.get("type") == ["integer", "string"]

    lit = schema_from_signature(_literal)["properties"]["mode"]
    assert set(lit["enum"]) == {"on", "off"}

    enum_schema = schema_from_signature(_enum)
    assert "$defs" in enum_schema or "a" in str(enum_schema["properties"]["k"])
    dumped = str(enum_schema)
    assert "a" in dumped and "b" in dumped

    model = schema_from_signature(_model)
    item = model["properties"]["item"]
    assert item.get("type") == "object" or "$ref" in item or "properties" in item or "$defs" in model


def test_return_schema_is_included() -> None:
    schema = schema_from_signature(_plain)
    assert "return" in schema
    assert schema["return"]["type"] == "boolean"


def test_rejects_unknown_callable() -> None:
    with pytest.raises(TypeError):
        schema_from_signature(42)  # type: ignore[arg-type]
