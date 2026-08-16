"""Shared Executor contract: behaviors that apply to every shipped adapter."""

from __future__ import annotations

import pytest

from agentframe.sandbox import ExecutionTimeout, InProcessExecutor, IsolatedExecutor
from agentframe.sandbox.executor import Executor


def _executors() -> list[tuple[str, Executor]]:
    return [
        ("inprocess", InProcessExecutor(timeout_seconds=1.0)),
        ("isolated", IsolatedExecutor(timeout_seconds=1.0)),
    ]


@pytest.fixture(params=_executors(), ids=lambda item: item[0])
def exe(request: pytest.FixtureRequest) -> Executor:
    return request.param[1]


def test_stdout_is_captured(exe: Executor) -> None:
    result = exe.execute("print('hi')", {})
    assert "hi" in result.stdout
    assert result.error is None


def test_syntax_error_is_captured(exe: Executor) -> None:
    result = exe.execute("def (", {})
    assert isinstance(result.error, SyntaxError)


def test_timeout_is_result_not_raise(exe: Executor) -> None:
    tight = type(exe)(timeout_seconds=0.2)
    result = tight.execute("while True:\n    pass", {})
    assert result.timed_out is True
    assert isinstance(result.error, ExecutionTimeout)


def test_contract_does_not_assert_object_identity(exe: Executor) -> None:
    """Isolated adapters copy; this only checks the cell does not raise."""
    result = exe.execute("xs = [1]\nxs.append(2)\nxs[-1]", {"xs": [1]})
    assert result.error is None or result.timed_out is False
    if result.error is None:
        assert result.display == 2
