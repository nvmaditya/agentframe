"""Canonical example: pause after a non-terminating cell, then resume."""

from __future__ import annotations

from agentframe import Agent, AgentRuntime, InMemoryEventLog, InProcessExecutor, ScriptedModelClient
from agentframe.runtime import Paused


class Worker(Agent):
    def run(self, task: str) -> str:
        """Finish with a greeting."""
        ...


def run_example() -> str:
    events = InMemoryEventLog()
    runtime = AgentRuntime(
        model=ScriptedModelClient(["x = 1", "return_result('hello')"]),
        executor=InProcessExecutor(),
        events=events,
    )
    steps = runtime.iterate(Worker(), "greet")
    paused = next(steps)
    if not isinstance(paused, Paused):
        raise AssertionError("expected a pause after the first turn")
    if events.query(type="Termination"):
        raise AssertionError("must not terminate before resume")
    if not events.query(type="ModelTurn"):
        raise AssertionError("pre-pause history must remain on the log")
    try:
        next(steps)
    except StopIteration as done:
        if not events.query(type="Termination"):
            raise AssertionError("expected Termination after resume") from None
        return done.value
    raise AssertionError("expected a validated return on resume")


if __name__ == "__main__":
    print(run_example())
