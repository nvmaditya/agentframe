"""InProcessExecutor runs cells against live objects and rejects dangerous code."""

from __future__ import annotations

import pytest

from agentframe.sandbox import ExecutionTimeout, Executor, ForbiddenName, InProcessExecutor


@pytest.fixture
def exe() -> Executor:
    return InProcessExecutor(timeout_seconds=1.0)


def test_last_expression_is_display(exe: Executor) -> None:
    result = exe.execute("1 + 2", {})
    assert result.error is None
    assert result.display == 3
    assert result.timed_out is False


def test_stdout_is_captured(exe: Executor) -> None:
    result = exe.execute("print('hi')", {})
    assert "hi" in result.stdout
    assert result.error is None


def test_live_object_is_same_identity(exe: Executor) -> None:
    data = [1, 2, 3]
    result = exe.execute("data.append(4)\ndata", {"data": data})
    assert result.error is None
    assert data is result.display
    assert data == [1, 2, 3, 4]


def test_new_names_written_back(exe: Executor) -> None:
    ns: dict = {}
    exe.execute("x = 9", ns)
    assert ns["x"] == 9


def test_exception_is_captured_not_raised(exe: Executor) -> None:
    result = exe.execute("1/0", {})
    assert result.error is not None
    assert isinstance(result.error, ZeroDivisionError)
    assert result.display is None


@pytest.mark.adversarial
@pytest.mark.parametrize(
    "source",
    [
        "eval('1')",
        "exec('x=1')",
        "compile('1', '<x>', 'eval')",
        "input()",
        "open('/etc/passwd')",
        "breakpoint()",
        "().__class__.__bases__[0].__subclasses__()",
    ],
)
def test_dangerous_names_are_rejected(exe: Executor, source: str) -> None:
    result = exe.execute(source, {})
    assert result.error is not None
    assert not isinstance(result.error, ZeroDivisionError)


@pytest.mark.adversarial
def test_import_and_socket_are_rejected(exe: Executor) -> None:
    for source in ("import socket", "import os", "__import__('os')"):
        result = exe.execute(source, {})
        assert result.error is not None


@pytest.mark.adversarial
def test_infinite_loop_times_out() -> None:
    exe = InProcessExecutor(timeout_seconds=0.2)
    result = exe.execute("while True:\n    pass", {})
    assert result.timed_out is True
    assert isinstance(result.error, ExecutionTimeout)
    assert result.error.seconds == 0.2


def test_syntax_error_is_captured(exe: Executor) -> None:
    result = exe.execute("def (", {})
    assert isinstance(result.error, SyntaxError)


def test_empty_cell_is_ok(exe: Executor) -> None:
    result = exe.execute("", {})
    assert result.error is None
    assert result.display is None


def test_from_import_rejected_unless_allowlisted() -> None:
    blocked = InProcessExecutor().execute("from os import path", {})
    assert blocked.error is not None
    allowed = InProcessExecutor(allowed_imports=("math",)).execute(
        "from math import sqrt\nsqrt(4)", {}
    )
    assert allowed.error is None
    assert allowed.display == 2.0


def test_execution_timeout_carries_seconds() -> None:
    err = ExecutionTimeout(1.5)
    assert err.seconds == 1.5
    assert "1.5" in str(err)


def test_allowed_import_helper_still_blocks_others() -> None:
    exe = InProcessExecutor(allowed_imports=("math",))
    with pytest.raises(ForbiddenName):
        exe._import("os")
