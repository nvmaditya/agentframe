"""Canonical example: manager CodeAct cell calls a composed worker."""

from __future__ import annotations

from agentframe import Agent, AgentRuntime, InMemoryEventLog, InProcessExecutor, ScriptedModelClient
from agentframe.compose import compose


class Worker(Agent):
    def shout(self, text: str) -> str:
        """Uppercase text."""
        return text.upper()


class Manager(Agent):
    """Delegate emphasis to the worker field."""

    def run(self, task: str) -> str:
        """Return the worker's shout of the task."""
        ...


def run_example() -> str:
    manager = compose(Manager(), worker=Worker())
    runtime = AgentRuntime(
        model=ScriptedModelClient(["return_result(self.worker.shout(task))"]),
        executor=InProcessExecutor(),
        events=InMemoryEventLog(),
    )
    return runtime.run(manager, "hello")


if __name__ == "__main__":
    print(run_example())
