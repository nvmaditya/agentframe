from __future__ import annotations

import inspect
from typing import Any, Callable, get_type_hints

from pydantic import TypeAdapter, create_model


def schema_from_signature(fn: Callable[..., Any]) -> dict[str, Any]:
    """Build a JSON Schema object from ``fn``'s parameters and return annotation.

    The returned dict is a JSON Schema ``object`` of the parameters (``self`` /
    ``cls`` omitted) plus a ``return`` key for the return annotation's schema
    when one is present.
    """
    if not callable(fn):
        raise TypeError(f"schema_from_signature expected a callable, got {type(fn)!r}")

    hints = get_type_hints(fn)
    signature = inspect.signature(fn)
    fields: dict[str, Any] = {}
    for name, param in signature.parameters.items():
        if name in {"self", "cls"}:
            continue
        annotation = hints.get(name, Any)
        if param.default is inspect.Parameter.empty:
            fields[name] = (annotation, ...)
        else:
            fields[name] = (annotation, param.default)

    model = create_model(f"{getattr(fn, '__name__', 'fn')}Params", **fields)
    schema = model.model_json_schema()
    schema.pop("title", None)

    if "return" in hints:
        schema["return"] = TypeAdapter(hints["return"]).json_schema()
        schema["return"].pop("title", None)
    return schema
