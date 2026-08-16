from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ExecutionTimeout(Exception):
    def __init__(self, seconds: float) -> None:
        super().__init__(f"cell exceeded {seconds}s")
        self.seconds = seconds


class ForbiddenName(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"forbidden name in cell: {name}")
        self.name = name


@dataclass
class ExecutionResult:
    stdout: str = ""
    stderr: str = ""
    display: Any = None
    error: Exception | None = None
    timed_out: bool = False
