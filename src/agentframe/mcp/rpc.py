from __future__ import annotations

from typing import Any

from agentframe.mcp.errors import McpError


def encode_request(id: int | None, method: str, params: dict[str, Any]) -> dict[str, Any]:
    message: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params}
    if id is not None:
        message["id"] = id
    return message


def decode_response(message: dict[str, Any]) -> Any:
    if "error" in message:
        err = message["error"] or {}
        raise McpError(str(err.get("message") or err))
    return message.get("result")
