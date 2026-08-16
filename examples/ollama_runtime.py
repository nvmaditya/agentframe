"""Shared Ollama ModelClient for the live examples.

Strips markdown fences so local models can emit ```python cells.
Override host/model with OLLAMA_HOST and OLLAMA_MODEL.
"""

from __future__ import annotations

import os

from agentframe import AgentRuntime, InMemoryEventLog, InProcessExecutor, OpenAICompatibleClient
from agentframe.runtime import ModelMessage, ModelResponse

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")


def strip_fences(text: str) -> str:
    lines = text.strip().splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def clean_cell(text: str) -> str:
    """Drop markdown fences and echoed object-repr assignments local models copy."""
    lines = [
        line
        for line in strip_fences(text).splitlines()
        if "object at 0x" not in line.lower()
        and "InMemoryEventLog(" not in line
        and not line.strip().startswith("events.")
    ]
    cleaned = "\n".join(lines).strip()
    for line in reversed(lines):
        if "return_result(" in line:
            return cleaned or line.strip()
    return cleaned or strip_fences(text)


class OllamaClient:
    def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
        host = (base_url or DEFAULT_HOST).rstrip("/")
        if host.endswith("/v1"):
            host = host[:-3]
        self._inner = OpenAICompatibleClient(
            base_url=f"{host}/v1",
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            model=model or DEFAULT_MODEL,
            timeout_seconds=180.0,
            temperature=0,
        )

    def complete(self, messages: list[ModelMessage]) -> ModelResponse:
        hint = ModelMessage(
            role="user",
            content=(
                "Write only a Python cell. Do not restate field previews. "
                "Use names already in scope (self, arguments). "
                "Finish with return_result(...). No markdown."
            ),
        )
        response = self._inner.complete([*messages, hint])
        return ModelResponse(content=clean_cell(response.content), raw=response.raw)


def ollama_runtime(model: str | None = None) -> AgentRuntime:
    return AgentRuntime(
        model=OllamaClient(model=model),
        executor=InProcessExecutor(),
        events=InMemoryEventLog(),
    )
