"""Canonical example: CodeAct indexes a live list the prompt never fully sees."""

from __future__ import annotations

from agentframe import Agent, AgentRuntime, InMemoryEventLog, InProcessExecutor, ScriptedModelClient


class Indexer(Agent):
    """Read values out of a large list by writing Python."""

    def run(self, data: list[int]) -> int:
        """Return the last element of data."""
        ...


def run_example() -> int:
    data = list(range(100))
    events = InMemoryEventLog()
    runtime = AgentRuntime(
        model=ScriptedModelClient(["return_result(data[-1])"]),
        executor=InProcessExecutor(),
        events=events,
    )
    value = runtime.run(Indexer(), data)
    dumped = str([e.payload for e in events.query()])
    if "50" in dumped:
        raise AssertionError("middle of the list leaked into event payloads")
    return value


if __name__ == "__main__":
    print(run_example())
