"""In-repo MCP echo fixture. Speaks Content-Length JSON-RPC on stdio."""

from __future__ import annotations

import json
import sys
from typing import Any


def handle(method: str, params: dict[str, Any]) -> Any:
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {"name": "echo-fixture", "version": "0"},
        }
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "echo",
                    "description": "Echo text",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                }
            ]
        }
    if method == "tools/call":
        if params.get("name") != "echo":
            return {"content": [{"type": "text", "text": "unknown"}], "isError": True}
        text = (params.get("arguments") or {}).get("text", "")
        return {"content": [{"type": "text", "text": text}], "isError": False}
    if method == "resources/list":
        return {"resources": [{"uri": "memo://1", "name": "one"}]}
    if method == "resources/read":
        uri = params.get("uri", "")
        return {"contents": [{"uri": uri, "mimeType": "text/plain", "text": f"body:{uri}"}]}
    if method == "prompts/get":
        name = params.get("name", "")
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": f"prompt:{name}"},
                }
            ]
        }
    return {"error": {"code": -32601, "message": f"unknown method {method}"}}


def _read_message() -> dict[str, Any] | None:
    header = b""
    while b"\r\n\r\n" not in header:
        chunk = sys.stdin.buffer.read(1)
        if not chunk:
            return None
        header += chunk
    header_text, _sep, rest = header.partition(b"\r\n\r\n")
    length = 0
    for line in header_text.decode("ascii", errors="replace").split("\r\n"):
        if line.lower().startswith("content-length:"):
            length = int(line.split(":", 1)[1].strip())
    body = rest
    while len(body) < length:
        chunk = sys.stdin.buffer.read(length - len(body))
        if not chunk:
            return None
        body += chunk
    return json.loads(body.decode("utf-8"))


def _write_message(message: dict[str, Any]) -> None:
    raw = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def main() -> None:
    while True:
        incoming = _read_message()
        if incoming is None:
            return
        method = incoming.get("method", "")
        params = incoming.get("params") or {}
        req_id = incoming.get("id")
        if method.startswith("notifications/"):
            handle(method, params)
            continue
        result = handle(method, params)
        if isinstance(result, dict) and "error" in result:
            _write_message({"jsonrpc": "2.0", "id": req_id, "error": result["error"]})
        else:
            _write_message({"jsonrpc": "2.0", "id": req_id, "result": result})


if __name__ == "__main__":
    main()
