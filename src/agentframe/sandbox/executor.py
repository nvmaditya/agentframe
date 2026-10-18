from __future__ import annotations

from abc import ABC, abstractmethod

from agentframe.sandbox.result import ExecutionResult


class Executor(ABC):
    keeps_live_objects: bool = False

    @abstractmethod
    def execute(
        self,
        source: str,
        namespace: dict,
        *,
        timeout_seconds: float | None = None,
    ) -> ExecutionResult:
        """Run ``source`` against ``namespace``. Never raises for cell errors.

        ``timeout_seconds`` overrides this executor's own deadline for one call.
        """
