from __future__ import annotations

from abc import ABC, abstractmethod

from agentframe.sandbox.result import ExecutionResult


class Executor(ABC):
    keeps_live_objects: bool = False

    @abstractmethod
    def execute(self, source: str, namespace: dict) -> ExecutionResult:
        """Run ``source`` against ``namespace``. Never raises for cell errors."""
