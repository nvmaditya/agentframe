from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class ModelMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class ModelResponse:
    content: str
    raw: Any = None


class ModelClient(Protocol):
    def complete(self, messages: list[ModelMessage]) -> ModelResponse: ...


class ScriptExhausted(RuntimeError):
    pass


class ScriptedModelClient:
    """Deterministic ModelClient for tests and Feature/E2E."""

    def __init__(self, turns: list[str]) -> None:
        self._turns = list(turns)
        self._i = 0
        self.seen: list[list[ModelMessage]] = []

    @property
    def calls(self) -> int:
        return self._i

    def complete(self, messages: list[ModelMessage]) -> ModelResponse:
        self.seen.append(list(messages))
        if self._i >= len(self._turns):
            raise ScriptExhausted("scripted ModelClient has no remaining turns")
        content = self._turns[self._i]
        self._i += 1
        return ModelResponse(content=content)
