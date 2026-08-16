"""Helper agent: tools work without a model; scripted loop uses the real class."""

from __future__ import annotations

import pytest

from agentframe import AgentRuntime, InMemoryEventLog, InProcessExecutor, ScriptedModelClient
from examples.ollama_helper import Helper, ask, run_example


def test_calculate_allows_arithmetic_only() -> None:
    helper = Helper()
    assert helper.calculate("6 * 7") == 42.0
    assert helper.calculate("17 + 19") == 36.0
    with pytest.raises(ValueError):
        helper.calculate("__import__('os')")


def test_remember_and_recall() -> None:
    helper = Helper()
    assert helper.remember("name", "Ada") == "Ada"
    assert helper.recall("name") == "Ada"
    assert helper.recall("missing") == ""


def test_scripted_helper_calculates() -> None:
    runtime = AgentRuntime(
        model=ScriptedModelClient(["return_result(str(int(self.calculate('6 * 7'))))"]),
        executor=InProcessExecutor(),
        events=InMemoryEventLog(),
    )
    assert run_example("What is 6 * 7?", runtime=runtime) == "42"


def test_scripted_helper_remembers() -> None:
    runtime = AgentRuntime(
        model=ScriptedModelClient(
            ["self.remember('name', 'Ada')\nreturn_result(self.recall('name'))"]
        ),
        executor=InProcessExecutor(),
        events=InMemoryEventLog(),
    )
    assert run_example("What is my name?", runtime=runtime) == "Ada"


def test_ask_survives_turn_limit() -> None:
    runtime = AgentRuntime(
        model=ScriptedModelClient(["x = 1"] * 6),
        executor=InProcessExecutor(),
        events=InMemoryEventLog(),
    )
    text = ask(Helper(), "hi", runtime=runtime)
    assert "couldn't finish" in text.lower()
