"""Agent field binding, method catalog, and strategy declarations."""

from __future__ import annotations

from typing import Literal

import pytest

from agentframe.core import (
    Agent,
    CodeActStrategy,
    PredictStrategy,
    RuntimeUnboundError,
    strategy,
)


def test_required_fields_are_constructor_kwargs() -> None:
    class Box(Agent):
        label: str

    box = Box(label="x")
    assert box.label == "x"
    with pytest.raises(TypeError, match="label"):
        Box()
    with pytest.raises(TypeError, match="extra"):
        Box(label="x", extra=1)


def test_mutable_defaults_are_not_shared() -> None:
    class NoteTaker(Agent):
        notes: list[str] = []

    a = NoteTaker()
    b = NoteTaker()
    a.notes.append("one")
    assert b.notes == []


def test_reserved_field_names_fail_at_class_body() -> None:
    with pytest.raises(TypeError, match="events"):

        class Bad(Agent):
            events: str


def test_real_body_is_deterministic_ellipsis_is_agentic() -> None:
    class Worker(Agent):
        def helper(self, n: int) -> int:
            """Add one."""
            return n + 1

        def go(self, n: int) -> int:
            """Do the work."""
            ...

    assert "helper" in Worker.__agentframe_tools__
    assert "go" in Worker.__agentframe_agentic__
    assert isinstance(Worker.__agentframe_agentic__["go"].strategy, CodeActStrategy)
    worker = Worker()
    assert worker.helper(1) == 2


def test_docstring_then_ellipsis_is_still_agentic() -> None:
    class Worker(Agent):
        def go(self) -> str:
            """A docstring, then ellipsis."""
            ...

    assert "go" in Worker.__agentframe_agentic__


def test_underscore_methods_are_not_published() -> None:
    class Worker(Agent):
        def _secret(self) -> int:
            return 1

        def visible(self) -> int:
            return 2

        def run(self) -> int:
            ...

    assert "_secret" not in Worker.__agentframe_tools__
    assert "visible" in Worker.__agentframe_tools__
    worker = Worker()
    assert worker._secret() == 1


def test_strategy_predict_attaches_without_changing_signature() -> None:
    class Worker(Agent):
        @strategy(PredictStrategy(max_retries=2))
        def classify(self, text: str) -> Literal["a", "b"]:
            """Classify."""
            ...

    spec = Worker.__agentframe_agentic__["classify"]
    assert isinstance(spec.strategy, PredictStrategy)
    assert spec.strategy.max_retries == 2
    assert spec.fn.__name__ == "classify"


def test_strategy_on_real_body_is_load_time_error() -> None:
    with pytest.raises(TypeError, match="strategy"):

        class Worker(Agent):
            @strategy()
            def helper(self) -> int:
                return 1


def test_agentic_call_without_runtime_raises() -> None:
    class Worker(Agent):
        def run(self, task: str) -> str:
            ...

    with pytest.raises(RuntimeUnboundError, match="run"):
        Worker().run("hi")
