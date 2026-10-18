"""Process-isolated Executor. Uses gVisor when ``runsc`` is on PATH."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_WORKER = Path(__file__).resolve().with_name("_isolated_worker.py")

from agentframe.sandbox.executor import Executor
from agentframe.sandbox.result import ExecutionResult, ExecutionTimeout, ForbiddenName

_KNOWN_ERRORS: dict[str, type[Exception]] = {
    "ZeroDivisionError": ZeroDivisionError,
    "SyntaxError": SyntaxError,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "NameError": NameError,
    "RuntimeError": RuntimeError,
    "PermissionError": PermissionError,
    "OSError": OSError,
}


def gvisor_available() -> bool:
    path = shutil.which("runsc")
    if path is None:
        return False
    try:
        completed = subprocess.run(
            [path, "--version"],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _jsonable_namespace(namespace: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in namespace.items():
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            continue
        out[str(key)] = value
    return out


def _rebuild_error(payload: dict[str, Any]) -> Exception | None:
    type_name = payload.get("error_type")
    if not type_name:
        return None
    msg = str(payload.get("error_msg") or type_name)
    if type_name == "ExecutionTimeout":
        seconds = payload.get("timeout_seconds")
        return ExecutionTimeout(float(seconds) if seconds is not None else 0.0)
    if type_name == "ForbiddenName":
        return ForbiddenName(str(payload.get("forbidden_name") or msg))
    cls = _KNOWN_ERRORS.get(type_name, Exception)
    return cls(msg)


class IsolatedExecutor(Executor):
    """Run a cell in a child process. Optional ``runsc`` wrap when present."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        use_gvisor: bool | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.use_gvisor = gvisor_available() if use_gvisor is None else use_gvisor

    def execute(
        self,
        source: str,
        namespace: dict,
        *,
        timeout_seconds: float | None = None,
    ) -> ExecutionResult:
        limit = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        payload = {
            "source": source,
            "namespace": _jsonable_namespace(namespace),
            "timeout_seconds": limit,
        }
        cmd = [sys.executable, "-I", str(_WORKER)]
        if self.use_gvisor:
            runsc = shutil.which("runsc")
            if runsc:
                cmd = [runsc, "--rootless", "do", "--network=none", "--", *cmd]
        try:
            completed = subprocess.run(
                cmd,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=limit + 1.0,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                timed_out=True,
                error=ExecutionTimeout(limit),
            )
        if completed.returncode != 0:
            err = completed.stderr.strip() or completed.stdout.strip() or "isolated worker failed"
            return ExecutionResult(stderr=completed.stderr, error=RuntimeError(err))
        try:
            data = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return ExecutionResult(
                stdout=completed.stdout,
                stderr=completed.stderr,
                error=RuntimeError("isolated worker returned non-JSON"),
            )
        return ExecutionResult(
            stdout=str(data.get("stdout") or ""),
            stderr=str(data.get("stderr") or ""),
            display=data.get("display"),
            error=_rebuild_error(data),
            timed_out=bool(data.get("timed_out")),
        )
