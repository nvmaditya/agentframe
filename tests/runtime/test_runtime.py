"""AgentRuntime: Predict retry, CodeAct live objects, validated termination."""

from __future__ import annotations

from typing import Literal

import pytest

from agentframe import (
    Agent,
    AgentRuntime,
    CodeActStrategy,
    InMemoryEventLog,
    InProcessExecutor,
    IsolatedExecutor,
    PredictStrategy,
    strategy,
)
from agentframe.runtime import ScriptedModelClient, TurnLimitExceeded


class Classifier(Agent):
    @strategy(PredictStrategy(max_retries=2))
    def run(self, text: str) -> Literal["spam", "ham"]:
        """Classify text as spam or ham."""
        ...


class Worker(Agent):
    def shout(self, text: str) -> str:
        """Uppercase."""
        return text.upper()

    def run(self, who: str) -> str:
        """Greet who."""
        ...


class Indexer(Agent):
    def run(self, data: list[int]) -> int:
        """Return the last item of data by indexing it."""
        ...


def _runtime(turns: list[str]) -> tuple[AgentRuntime, InMemoryEventLog, ScriptedModelClient]:
    events = InMemoryEventLog()
    model = ScriptedModelClient(turns)
    runtime = AgentRuntime(model=model, executor=InProcessExecutor(), events=events)
    return runtime, events, model


def test_predict_retries_invalid_then_returns_typed() -> None:
    runtime, events, _ = _runtime(['"nope"', '"spam"'])
    result = runtime.run(Classifier(), "buy now")
    assert result == "spam"
    assert any(e.type == "ValidationError" for e in events.query())
    assert events.query(type="Termination")


def test_codeact_pass_by_reference_and_preview_bounds() -> None:
    data = list(range(100))
    runtime, events, model = _runtime(["return_result(data[-1])"])
    result = runtime.run(Indexer(), data)
    assert result == 99
    assert result is data[-1]
    dumped = " ".join(str(e.payload) for e in events.query())
    assert "50" not in dumped


def test_runtime_refuses_an_executor_that_cannot_keep_the_live_object() -> None:
    events = InMemoryEventLog()
    model = ScriptedModelClient(["return_result(1)"])
    with pytest.raises(
        TypeError,
        match="keeps the live object, its methods, and return_result",
    ):
        AgentRuntime(model=model, executor=IsolatedExecutor(), events=events)
    assert model.calls == 0
    assert list(events.query()) == []


def test_codeact_returns_the_live_tail_of_a_large_list() -> None:
    """Regression lock: the tail stays the caller's object, and the middle stays out of the log."""
    sentinel = "middle-sentinel-7c1e"
    tail = "live-tail-7c1e"
    data = [0] * 10_000
    data[5_000] = sentinel
    data[-1] = tail

    class BulkIndexer(Agent):
        def run(self, rows: list) -> str:
            """Return the last item of rows by indexing it."""
            ...

    runtime, events, _ = _runtime(["return_result(rows[-1])"])
    result = runtime.run(BulkIndexer(), data)
    assert result == "live-tail-7c1e"
    assert result is data[-1]
    dumped = " ".join(str(e.payload) for e in events.query())
    assert sentinel not in dumped


def test_fenced_cell_returns_the_annotated_value() -> None:
    class Speaker(Agent):
        @strategy(CodeActStrategy(max_turns=1))
        def run(self) -> str:
            """Say ok."""
            ...

    cell = "```python\nreturn_result('ok')\n```"
    runtime, _, _ = _runtime([cell])
    assert runtime.run(Speaker()) == "ok"


def test_prose_is_an_observation_and_the_next_cell_returns() -> None:
    """Regression lock: prose is not rewritten into a successful return."""

    class Speaker(Agent):
        def run(self) -> str:
            """Say ok."""
            ...

    runtime, events, _ = _runtime(["not python!!!", "return_result('ok')"])
    assert runtime.run(Speaker()) == "ok"
    texts = [e.payload.get("text", "") for e in events.query(type="Observation")]
    assert any("SyntaxError" in text for text in texts)


def test_cell_past_the_strategy_timeout_is_an_observation() -> None:
    class Slow(Agent):
        @strategy(CodeActStrategy(max_turns=2, cell_timeout_seconds=0.05))
        def run(self) -> str:
            """Return after a slow cell."""
            ...

    events = InMemoryEventLog()
    runtime = AgentRuntime(
        model=ScriptedModelClient(
            [
                "import time\ntime.sleep(0.3)\nreturn_result('late')",
                "return_result('ok')",
            ]
        ),
        executor=InProcessExecutor(timeout_seconds=10, allowed_imports=("time",)),
        events=events,
    )
    assert runtime.run(Slow()) == "ok"
    assert events.query(type="Execution")[0].payload["timed_out"] is True
    texts = [e.payload.get("text", "") for e in events.query(type="Observation")]
    assert any("ExecutionTimeout" in text for text in texts)


def test_validated_termination_rejects_then_accepts() -> None:
    runtime, events, _ = _runtime(["return_result(1)", "return_result(self.shout('ok'))"])
    result = runtime.run(Worker(), "ada")
    assert result == "OK"
    assert len(events.query(type="ValidationError")) == 1


def test_missing_method_fails_before_model() -> None:
    runtime, _, model = _runtime(["should not be called"])
    with pytest.raises(AttributeError):
        runtime.run(Worker(), method="nope")
    assert model.calls == 0


def test_deterministic_method_is_not_runnable_as_entry() -> None:
    runtime, _, _ = _runtime(["should not be called"])
    with pytest.raises(TypeError, match="not an agentic"):
        runtime.run(Worker(), method="shout")


def test_predict_raises_after_retries_exhausted() -> None:
    runtime, events, _ = _runtime(['"nope"', '"still-nope"', '"nope-again"'])
    with pytest.raises(Exception):
        runtime.run(Classifier(), "buy now")
    assert events.query(type="ValidationError")


class Short(Agent):
    @strategy(CodeActStrategy(max_turns=1))
    def run(self, task: str) -> str:
        """One turn only."""
        ...


def test_turn_limit_raises() -> None:
    runtime, _, _ = _runtime(["x = 1"])
    with pytest.raises(TurnLimitExceeded):
        runtime.run(Short(), "z")


class ToolBox:
    def ping(self, n: int) -> int:
        """Echo n."""
        return n


class WithField(Agent):
    box: ToolBox

    def run(self, task: str) -> int:
        """Call the composed field."""
        ...


def test_composed_field_methods_are_callable_from_a_cell() -> None:
    runtime, _, model = _runtime(["return_result(self.box.ping(7))"])
    result = runtime.run(WithField(box=ToolBox()), "go")
    assert result == 7
    system = model.seen[0][0].content
    assert "self.box.ping" in system


def test_composed_field_is_a_bare_name_in_the_cell() -> None:
    runtime, _, _ = _runtime(["return_result(box.ping(7))"])
    assert runtime.run(WithField(box=ToolBox()), "go") == 7


class Probe(Agent):
    def run(self, task: str) -> bool:
        """Whether events is a bare name."""
        ...


def test_reserved_events_is_not_a_bare_cell_name() -> None:
    runtime, _, _ = _runtime(["return_result('events' in locals())"])
    assert runtime.run(Probe(), "t") is False


def test_codeact_records_stdout_and_errors_as_observations() -> None:
    runtime, events, _ = _runtime(["print('hi')\n1/0", "return_result('ok')"])
    assert runtime.run(Worker(), "ada") == "ok"
    texts = [e.payload.get("text", "") for e in events.query(type="Observation")]
    assert any("hi" in t or "ZeroDivision" in t for t in texts)


def test_context_is_three_regions() -> None:
    runtime, _, model = _runtime(["return_result('hi')"])

    class Tiny(Agent):
        def run(self, task: str) -> str:
            """Say hi."""
            ...

    runtime.run(Tiny(), "t")
    messages = model.seen[0]
    assert messages[0].role == "system"
    assert messages[-1].role == "user"
    assert any(m.role == "user" for m in messages)
