from __future__ import annotations

from typing import Any, Callable

from agentframe.mcp.errors import McpError


class FakeMcpTransport:
    """In-process JSON-RPC double. No sockets, no subprocesses."""

    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.opened = False
        self.closed = False

    def handle(self, method: str, fn: Callable[[dict[str, Any]], Any]) -> None:
        self.handlers[method] = fn

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.closed = True

    def request(self, method: str, params: dict[str, Any]) -> Any:
        self.calls.append((method, params))
        if method not in self.handlers:
            raise McpError(f"JSON-RPC method not registered: {method}")
        return self.handlers[method](params)
