"""Interface-capability scenarios.

CI runs these against ScriptedModelClient (does the harness expose the
primitive). Set AGENTFRAME_CAPABILITY=1 and provide a real ModelClient to
run the same scenarios against a live model.
"""

from __future__ import annotations

import pytest

from agentframe import (
    Agent,
    AgentRuntime,
    InMemoryEventLog,
    InProcessExecutor,
    PredictStrategy,
    strategy,
)
from agentframe.runtime import ScriptedModelClient


pytestmark = pytest.mark.capability


class Box(Agent):
    count: int = 0

    def bump(self) -> int:
        """Increment count and return it."""
        self.count += 1
        return self.count

    @strategy(PredictStrategy())
    def label(self, text: str) -> str:
        """Echo a short label."""
        ...

    def run(self, task: str) -> int:
        """Bump twice and return the count."""
        ...


def test_typed_predict_and_stateful_bump() -> None:
    events = InMemoryEventLog()
    runtime = AgentRuntime(
        model=ScriptedModelClient(['"ok"', "self.bump()\nself.bump()\nreturn_result(self.count)"]),
        executor=InProcessExecutor(),
        events=events,
    )
    agent = Box()
    assert runtime.run(agent, "x", method="label") == "ok"
    assert runtime.run(agent, "go") == 2
    assert agent.count == 2
