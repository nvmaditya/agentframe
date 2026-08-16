from __future__ import annotations

import inspect
from typing import Any, Callable

from agentframe.contracts import schema_from_signature
from agentframe.core.agent import Agent
from agentframe.core.catalog import AgenticSpec
from agentframe.runtime.model import ModelMessage
from agentframe.runtime.preview import preview


SYSTEM_PREFIX = (
    "You are completing an agentic Python method. "
    "Deterministic methods on self are ordinary callables. "
    "For CodeAct, write a Python cell. Call return_result(value) to finish. "
    "For Predict, reply with JSON matching the return type."
)


def field_catalog(agent: Agent) -> list[str]:
    lines: list[str] = []
    for name, value in vars(agent).items():
        if name.startswith("_") or name in {"events"}:
            continue
        if isinstance(value, (str, bytes, int, float, bool, type(None))):
            continue
        for attr, member in _public_callables(value):
            extra = getattr(member, "__tool_schema__", None)
            try:
                schema = extra if isinstance(extra, dict) else schema_from_signature(member)
            except (TypeError, ValueError):
                schema = {}
            doc = inspect.getdoc(member) or ""
            try:
                sig = str(inspect.signature(member))
            except (TypeError, ValueError):
                sig = "(...)"
            lines.append(f"self.{name}.{attr}{sig} {doc} {schema.get('return', '')}".strip())
    return lines


def _public_callables(obj: Any) -> list[tuple[str, Any]]:
    found: dict[str, Any] = {}
    for src in (type(obj).__dict__, getattr(obj, "__dict__", {})):
        for attr, member in src.items():
            if attr.startswith("_") or not callable(member):
                continue
            found[attr] = getattr(obj, attr, member)
    return list(found.items())


def static_prefix(agent: Agent, spec: AgenticSpec) -> str:
    tool_lines = []
    for name, fn in type(agent).__agentframe_tools__.items():
        tool_lines.append(f"- self.{name}{inspect.signature(fn)}: {inspect.getdoc(fn) or ''}".strip())
    agentic_lines = [
        f"- self.{name}{inspect.signature(item.fn)} [agentic]"
        for name, item in type(agent).__agentframe_agentic__.items()
        if name != spec.name
    ]
    composed = field_catalog(agent)
    return "\n".join(
        [
            SYSTEM_PREFIX,
            f"Class: {inspect.getdoc(type(agent)) or type(agent).__name__}",
            f"Method: {spec.doc or spec.name}",
            f"Strategy: {type(spec.strategy).__name__}",
            "Tools:",
            *tool_lines,
            *agentic_lines,
            *([ "Field methods:", *composed] if composed else []),
        ]
    )


def bind_arguments(fn: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    signature = inspect.signature(fn)
    bound = signature.bind_partial(*((None,) + args), **kwargs)
    # first param is self — drop it
    mapping = dict(bound.arguments)
    mapping.pop("self", None)
    return mapping
