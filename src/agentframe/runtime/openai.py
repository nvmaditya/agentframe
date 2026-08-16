from __future__ import annotations

import json
import urllib.error
import urllib.request

from agentframe.runtime.model import ModelMessage, ModelResponse


class OpenAICompatibleClient:
    """Chat Completions client. Constructed by the host, not by runtime.loop."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout_seconds: float = 60.0,
        temperature: float | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    def complete(self, messages: list[ModelMessage]) -> ModelResponse:
        payload: dict = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI-compatible HTTP {exc.code}: {body}") from exc
        content = data["choices"][0]["message"]["content"]
        return ModelResponse(content=content or "", raw=data)
