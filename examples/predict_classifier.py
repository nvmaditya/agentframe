"""Canonical example: PredictStrategy with a typed Literal return."""

from __future__ import annotations

from typing import Literal

from agentframe import (
    Agent,
    AgentRuntime,
    InMemoryEventLog,
    InProcessExecutor,
    PredictStrategy,
    ScriptedModelClient,
    strategy,
)


class Classifier(Agent):
    """Classify a short message."""

    @strategy(PredictStrategy(max_retries=2))
    def run(self, text: str) -> Literal["spam", "ham"]:
        """Return spam or ham."""
        ...


def run_example() -> str:
    runtime = AgentRuntime(
        model=ScriptedModelClient(['"nope"', '"ham"']),
        executor=InProcessExecutor(),
        events=InMemoryEventLog(),
    )
    return runtime.run(Classifier(), "hello friend")


if __name__ == "__main__":
    print(run_example())
