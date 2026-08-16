"""compose() assigns agents to fields. No extra base class required."""

from __future__ import annotations

from agentframe.compose import compose
from agentframe.core import Agent


class Worker(Agent):
    def shout(self, text: str) -> str:
        """Uppercase."""
        return text.upper()


class Manager(Agent):
    def run(self, task: str) -> str:
        """Delegate."""
        ...


def test_compose_assigns_worker_without_new_superclass() -> None:
    worker = Worker()
    manager = compose(Manager(), worker=worker)
    assert manager.worker is worker
    assert manager.worker.shout("hi") == "HI"
    assert not issubclass(Manager, type(compose))
    assert type(manager) is Manager
