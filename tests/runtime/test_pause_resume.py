"""Pause after a non-terminating turn; resume on the same log to a validated return."""

from __future__ import annotations

from agentframe import Agent, AgentRuntime, InMemoryEventLog, InProcessExecutor
from agentframe.runtime import Paused, ScriptedModelClient


class Worker(Agent):
    def run(self, task: str) -> str:
        """Finish with a string."""
        ...


def test_sync_run_still_completes() -> None:
    events = InMemoryEventLog()
    runtime = AgentRuntime(
        model=ScriptedModelClient(["return_result('done')"]),
        executor=InProcessExecutor(),
        events=events,
    )
    assert runtime.run(Worker(), "t") == "done"


def test_first_turn_pauses_then_resume_returns_and_keeps_history() -> None:
    events = InMemoryEventLog()
    runtime = AgentRuntime(
        model=ScriptedModelClient(["x = 1", "return_result('ok')"]),
        executor=InProcessExecutor(),
        events=events,
    )
    steps = runtime.iterate(Worker(), "t")
    paused = next(steps)
    assert isinstance(paused, Paused)
    before = [e.type for e in events.query()]
    assert "ModelTurn" in before
    assert "Termination" not in before
    try:
        next(steps)
    except StopIteration as done:
        assert done.value == "ok"
    else:
        raise AssertionError("expected validated return on resume")
    assert events.query(type="Termination")
    assert [e.type for e in events.query()][: len(before)] == before
