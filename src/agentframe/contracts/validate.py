from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter, create_model

_JSON_TO_PY = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validate_output(value: Any, annotation: Any) -> Any:
    """Coerce ``value`` to ``annotation`` via Pydantic v2.

    ``annotation`` is a Python type, or a JSON Schema object (dict) used
    by MCP tool input schemas. Raises ``pydantic.ValidationError`` on
    failure. Never returns a half-valid value.
    """
    if isinstance(annotation, dict):
        return TypeAdapter(_annotation_from_schema(annotation)).validate_python(value)
    return TypeAdapter(annotation).validate_python(value)


def _annotation_from_schema(schema: dict[str, Any]) -> Any:
    props = schema.get("properties")
    if isinstance(props, dict):
        required = set(schema.get("required") or [])
        fields: dict[str, Any] = {}
        for name, prop in props.items():
            py = _JSON_TO_PY.get((prop or {}).get("type", ""), Any)
            fields[name] = (py, ...) if name in required else (py, None)
        if fields:
            return create_model("JsonSchemaArgs", **fields)
    json_type = schema.get("type")
    return _JSON_TO_PY.get(json_type, dict) if json_type else dict
