"""Standalone IsolatedExecutor child. No agentframe import — that would preload Path/socket."""

from __future__ import annotations

import ast
import builtins
import io
import json
import sys
import time
from contextlib import redirect_stderr, redirect_stdout

FORBIDDEN_NAMES = frozenset(
    {"eval", "exec", "compile", "input", "open", "breakpoint", "__import__"}
)
FORBIDDEN_ATTRS = frozenset({"__subclasses__", "__globals__", "__code__", "__builtins__"})
ALLOWED_DUNDER = frozenset({"__name__", "__doc__"})


class ExecutionTimeout(Exception):
    def __init__(self, seconds: float) -> None:
        super().__init__(f"cell exceeded {seconds}s")
        self.seconds = seconds


class ForbiddenName(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"forbidden name in cell: {name}")
        self.name = name


def _forbidden_attr(name: object) -> bool:
    if name in FORBIDDEN_ATTRS:
        return True
    return isinstance(name, str) and name.startswith("__") and name not in ALLOWED_DUNDER


def _safe_getattr(obj: object, name: object, *default: object) -> object:
    if _forbidden_attr(name):
        raise ForbiddenName(str(name))
    if default:
        return getattr(obj, name, default[0])
    return getattr(obj, name)


def _reject(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise ForbiddenName(node.id)
        if isinstance(node, ast.Attribute) and _forbidden_attr(node.attr):
            raise ForbiddenName(node.attr)
        if isinstance(node, ast.Import):
            for alias in node.names:
                raise ForbiddenName(f"import {alias.name}")
        if isinstance(node, ast.ImportFrom):
            raise ForbiddenName(f"from {node.module} import")


def _split_last_expr(tree: ast.Module) -> tuple[str, str | None]:
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = tree.body[-1]
        rest_body = tree.body[:-1]
        rest = ast.unparse(ast.Module(body=rest_body, type_ignores=[])) if rest_body else ""
        return rest, ast.unparse(last)
    if not tree.body:
        return "", None
    return ast.unparse(tree), None


def _builtins() -> dict[str, object]:
    allowed = {
        name: getattr(builtins, name)
        for name in dir(builtins)
        if not name.startswith("_") and name not in FORBIDDEN_NAMES
    }
    allowed["getattr"] = _safe_getattr
    return allowed


def execute(source: str, namespace: dict, timeout_seconds: float) -> dict:
    try:
        tree = ast.parse(source)
        _reject(tree)
    except SyntaxError as exc:
        return _pack(error=exc)
    except ForbiddenName as exc:
        return _pack(error=exc)

    rest, expr = _split_last_expr(tree)
    loc = dict(namespace)
    loc["__builtins__"] = _builtins()
    deadline = time.monotonic() + timeout_seconds

    def tracer(_frame: object, _event: str, _arg: object) -> object:
        if time.monotonic() > deadline:
            raise ExecutionTimeout(timeout_seconds)
        return tracer

    stdout = io.StringIO()
    stderr = io.StringIO()
    display: object = None
    error: Exception | None = None
    timed_out = False
    try:
        sys.settrace(tracer)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            if rest:
                exec(compile(rest, "<cell>", "exec"), loc, loc)  # noqa: S102
            if expr:
                display = eval(compile(expr, "<cell>", "eval"), loc, loc)  # noqa: S307
    except ExecutionTimeout as exc:
        timed_out = True
        error = exc
        display = None
    except Exception as exc:  # noqa: BLE001
        error = exc
        display = None
    finally:
        sys.settrace(None)
    return _pack(
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
        display=display,
        error=error,
        timed_out=timed_out,
    )


def _jsonable(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return {"__repr__": repr(value)}


def _pack(
    *,
    stdout: str = "",
    stderr: str = "",
    display: object = None,
    error: Exception | None = None,
    timed_out: bool = False,
) -> dict:
    return {
        "stdout": stdout,
        "stderr": stderr,
        "display": _jsonable(display),
        "error_type": None if error is None else type(error).__name__,
        "error_msg": None if error is None else str(error),
        "timed_out": timed_out,
        "timeout_seconds": getattr(error, "seconds", None),
        "forbidden_name": getattr(error, "name", None),
    }


def main() -> None:
    for name in ("os", "pathlib", "socket", "urllib", "subprocess", "nt", "posix"):
        sys.modules.pop(name, None)
    payload = json.load(sys.stdin)
    result = execute(
        str(payload.get("source", "")),
        dict(payload.get("namespace") or {}),
        float(payload.get("timeout_seconds", 30)),
    )
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
