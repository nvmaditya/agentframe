"""Shared Ollama ModelClient for the live examples.

Strips markdown fences so local models can emit ```python cells.
Override host/model with OLLAMA_HOST and OLLAMA_MODEL.
"""

from __future__ import annotations

import ast
import os
import re

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


_PREVIEW_ASSIGN = re.compile(
    r"^(notes|task|text|who|data|remaining_turns)\s*="
)


def _drop_echo(line: str) -> bool:
    s = line.strip()
    return (
        "object at 0x" in s.lower()
        or "InMemoryEventLog(" in s
        or s.startswith("events.")
        or bool(_PREVIEW_ASSIGN.match(s))
    )


def _looks_like_prose(text: str) -> bool:
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith(("def ", "class ", "import ", "from ", "return ", "self.", "print(")):
            return False
        if "=" in s:
            return False
    return bool(text.strip())


def ensure_return(text: str) -> str:
    """If the model wrote a greeting or a string literal, make it a return_result cell."""
    if "return_result(" in text:
        return text
    stripped = text.strip()
    if not stripped:
        return text
    try:
        value = ast.literal_eval(stripped)
    except (SyntaxError, ValueError):
        value = None
    if isinstance(value, str):
        return f"return_result({stripped})"
    if _looks_like_prose(stripped):
        return f"return_result({stripped!r})"
    return text


def clean_cell(text: str) -> str:
    """Drop markdown fences and echoed object-repr assignments local models copy."""
    lines = [line for line in strip_fences(text).splitlines() if not _drop_echo(line)]
    cleaned = "\n".join(lines).strip()
    for line in reversed(lines):
        if "return_result(" in line:
            return cleaned or line.strip()
    return ensure_return(cleaned or strip_fences(text))


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
                "A greeting or plain-language answer must be "
                "return_result(\"your words\"). "
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
