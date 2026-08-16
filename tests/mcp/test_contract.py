"""Shared McpClient contract over fake, stdio fixture, and in-process HTTP."""

from __future__ import annotations

import json
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from agentframe.mcp import (
    FakeMcpTransport,
    McpClient,
    McpError,
    StdioTransport,
    StreamableHttpTransport,
)
from tests.fixtures.mcp_echo_server import handle
from tests.mcp.test_client import _echo_server

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "mcp_echo_server.py"


def _fake_client() -> Iterator[McpClient]:
    client = McpClient(_echo_server())
    client.connect()
    yield client
    client.close()


def _stdio_client() -> Iterator[McpClient]:
    transport = StdioTransport(sys.executable, (str(FIXTURE),))
    client = McpClient(transport)
    client.connect()
    yield client
    client.close()


def _http_client() -> Iterator[McpClient]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            message = json.loads(self.rfile.read(length) or b"{}")
            method = message.get("method", "")
            params = message.get("params") or {}
            req_id = message.get("id")
            if method.startswith("notifications/"):
                handle(method, params)
                self.send_response(204)
                self.end_headers()
                return
            result = handle(method, params)
            if isinstance(result, dict) and "error" in result:
                payload = {"jsonrpc": "2.0", "id": req_id, "error": result["error"]}
            else:
                payload = {"jsonrpc": "2.0", "id": req_id, "result": result}
            raw = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *_args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    client = McpClient(StreamableHttpTransport(f"http://{host}:{port}/mcp"))
    client.connect()
    try:
        yield client
    finally:
        client.close()
        server.shutdown()


@pytest.fixture(params=["fake", "stdio", "http"])
def client(request: pytest.FixtureRequest) -> Iterator[McpClient]:
    factories = {"fake": _fake_client, "stdio": _stdio_client, "http": _http_client}
    yield from factories[request.param]()


def test_contract_echo_tool(client: McpClient) -> None:
    result = client.echo(text="ping")
    assert result.text == "ping"
    assert result.is_error is False


def test_contract_resources_and_prompt(client: McpClient) -> None:
    assert "memo://1" in client.list_resources()
    assert "body:memo://1" in client.read_resource("memo://1").text
    assert client.get_prompt("hi").startswith("prompt:hi")


def test_contract_unknown_tool(client: McpClient) -> None:
    with pytest.raises(McpError):
        client.missing_tool()
