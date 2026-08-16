"""Child process for IsolatedExecutor. Reads JSON on stdin, writes JSON on stdout."""

from __future__ import annotations

import json
import sys
from typing import Any

from agentframe.sandbox.inprocess import InProcessExecutor
from agentframe.sandbox.result import ExecutionResult


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return {"__repr__": repr(value)}


def _pack(result: ExecutionResult) -> dict[str, Any]:
    error = result.error
    packed: dict[str, Any] = {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "display": _jsonable(result.display),
        "error_type": None if error is None else type(error).__name__,
        "error_msg": None if error is None else str(error),
        "timed_out": result.timed_out,
        "timeout_seconds": getattr(error, "seconds", None),
        "forbidden_name": getattr(error, "name", None),
    }
    return packed


def main() -> None:
    payload = json.load(sys.stdin)
    exe = InProcessExecutor(timeout_seconds=float(payload.get("timeout_seconds", 30)))
    namespace = dict(payload.get("namespace") or {})
    result = exe.execute(str(payload.get("source", "")), namespace)
    json.dump(_pack(result), sys.stdout)


if __name__ == "__main__":
    main()
