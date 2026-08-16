from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter


def validate_output(value: Any, annotation: Any) -> Any:
    """Coerce ``value`` to ``annotation`` via Pydantic v2.

    Raises ``pydantic.ValidationError`` on failure. Never returns a
    half-valid value.
    """
    return TypeAdapter(annotation).validate_python(value)
