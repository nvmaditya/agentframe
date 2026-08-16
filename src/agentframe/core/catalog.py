from __future__ import annotations

import ast
import inspect
import textwrap
from dataclasses import dataclass
from typing import Any, Callable

from agentframe.core.strategy import CodeActStrategy, PredictStrategy


@dataclass(frozen=True)
class AgenticSpec:
    name: str
    fn: Callable[..., Any]
    strategy: PredictStrategy | CodeActStrategy
    doc: str | None


def is_ellipsis_body(fn: Callable[..., Any]) -> bool:
    """True when the function body is only ``...`` (optionally after a docstring)."""
    try:
        source = textwrap.dedent(inspect.getsource(fn))
    except (OSError, TypeError):
        return False
    tree = ast.parse(source)
    func = tree.body[0]
    if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    body = list(func.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return (
        len(body) == 1
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and body[0].value.value is ...
    )
