from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from agentframe.mcp.errors import McpError
from agentframe.mcp.rpc import decode_response, encode_request


class StreamableHttpTransport:
    """POST JSON-RPC to an MCP Streamable HTTP endpoint (JSON response)."""

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.url = url
        self.headers = headers or {}
        self.timeout_seconds = timeout_seconds
        self._next_id = 1

    def open(self) -> None:
        return None

    def close(self) -> None:
        return None

    def request(self, method: str, params: dict[str, Any]) -> Any:
        if method.startswith("notifications/"):
            self._post(encode_request(None, method, params))
            return None
        req_id = self._next_id
        self._next_id += 1
        message = self._post(encode_request(req_id, method, params))
        if message is None:
            raise McpError("empty HTTP JSON-RPC response")
        return decode_response(message)

    def _post(self, message: dict[str, Any]) -> dict[str, Any] | None:
        data = json.dumps(message).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.headers,
        }
        request = urllib.request.Request(self.url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise McpError(f"HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise McpError(f"HTTP transport failed: {exc}") from exc
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise McpError(f"invalid JSON-RPC from HTTP: {exc}") from exc
