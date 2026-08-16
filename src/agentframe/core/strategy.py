from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class PredictStrategy:
    max_retries: int = 3
    argument_render_cap_bytes: int = 8192


@dataclass(frozen=True)
class CodeActStrategy:
    max_turns: int = 20
    cell_timeout_seconds: float = 30.0


def strategy(strat: Any = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark an agentic method and attach a strategy declaration."""
    if strat is None:
        attached = CodeActStrategy()
    elif isinstance(strat, type):
        attached = strat()
    else:
        attached = strat

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn.__agentframe_strategy__ = attached  # type: ignore[attr-defined]
        return fn

    return decorator
