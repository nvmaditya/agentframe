"""Canonical example: IsolatedExecutor prints from a child process."""

from __future__ import annotations

from agentframe import IsolatedExecutor


def run_example() -> str:
    result = IsolatedExecutor(timeout_seconds=5.0).execute("print('ok')", {})
    if result.error is not None:
        raise result.error
    return result.stdout


if __name__ == "__main__":
    print(run_example(), end="")
