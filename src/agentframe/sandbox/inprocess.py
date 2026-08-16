from __future__ import annotations

import ast
import builtins
import io
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from agentframe.sandbox.executor import Executor
from agentframe.sandbox.result import ExecutionResult, ExecutionTimeout, ForbiddenName

FORBIDDEN_NAMES = frozenset(
    {"eval", "exec", "compile", "input", "open", "breakpoint", "__import__"}
)
FORBIDDEN_ATTRS = frozenset({"__subclasses__", "__globals__", "__code__", "__builtins__"})


class InProcessExecutor(Executor):
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        allowed_imports: tuple[str, ...] = (),
        allowed_open_paths: tuple[str, ...] = (),
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.allowed_imports = frozenset(allowed_imports)
        self.allowed_open_paths = tuple(allowed_open_paths)

    def execute(self, source: str, namespace: dict[str, Any]) -> ExecutionResult:
        try:
            tree = ast.parse(source)
            self._reject(tree)
        except SyntaxError as exc:
            return ExecutionResult(error=exc)
        except ForbiddenName as exc:
            return ExecutionResult(error=exc)

        rest, expr = _split_last_expr(tree)
        loc = dict(namespace)
        loc["__builtins__"] = self._builtins()
        deadline = time.monotonic() + self.timeout_seconds

        def tracer(_frame: Any, _event: str, _arg: Any) -> Any:
            if time.monotonic() > deadline:
                raise ExecutionTimeout(self.timeout_seconds)
            return tracer

        stdout = io.StringIO()
        stderr = io.StringIO()
        display: Any = None
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
        except Exception as exc:  # noqa: BLE001 — cell errors are the result
            error = exc
            display = None
        finally:
            sys.settrace(None)

        for key, value in loc.items():
            if key != "__builtins__":
                namespace[key] = value
        return ExecutionResult(
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
            display=display,
            error=error,
            timed_out=timed_out,
        )

    def _reject(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                raise ForbiddenName(node.id)
            if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
                raise ForbiddenName(node.attr)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    if root not in self.allowed_imports:
                        raise ForbiddenName(f"import {alias.name}")
            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".", 1)[0]
                if root not in self.allowed_imports:
                    raise ForbiddenName(f"from {node.module} import")

    def _builtins(self) -> dict[str, Any]:
        allowed = {
            name: getattr(builtins, name)
            for name in dir(builtins)
            if not name.startswith("_") and name not in FORBIDDEN_NAMES
        }
        if self.allowed_imports:
            allowed["__import__"] = self._import
        return allowed

    def _import(self, name: str, *args: Any, **kwargs: Any) -> Any:
        root = name.split(".", 1)[0]
        if root not in self.allowed_imports:
            raise ForbiddenName(f"import {name}")
        return builtins.__import__(name, *args, **kwargs)


def _split_last_expr(tree: ast.Module) -> tuple[str, str | None]:
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = tree.body[-1]
        rest_body = tree.body[:-1]
        rest = ast.unparse(ast.Module(body=rest_body, type_ignores=[])) if rest_body else ""
        return rest, ast.unparse(last)
    if not tree.body:
        return "", None
    return ast.unparse(tree), None
