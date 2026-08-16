"""McpClient over FakeMcpTransport — connect, call, errors, resources, prompts."""

from __future__ import annotations

import pytest

from agentframe.mcp import FakeMcpTransport, McpClient, McpError, McpResult


def _echo_server() -> FakeMcpTransport:
    transport = FakeMcpTransport()
    transport.handle(
        "initialize",
        lambda _p: {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {"name": "echo", "version": "0"},
        },
    )
    transport.handle("notifications/initialized", lambda _p: None)
    transport.handle(
        "tools/list",
        lambda _p: {
            "tools": [
                {
                    "name": "echo",
                    "description": "Echo text",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                },
                {
                    "name": "list-issues",
                    "description": "hyphenated",
                    "inputSchema": {"type": "object", "properties": {}},
                },
            ]
        },
    )

    def call(params: dict) -> dict:
        name = params["name"]
        args = params.get("arguments") or {}
        if name == "echo":
            return {"content": [{"type": "text", "text": args["text"]}], "isError": False}
        if name == "list-issues":
            return {"content": [{"type": "text", "text": "ok"}], "isError": False}
        return {"content": [{"type": "text", "text": "nope"}], "isError": True}

    transport.handle("tools/call", call)
    transport.handle(
        "resources/list",
        lambda _p: {"resources": [{"uri": "memo://1", "name": "one"}]},
    )
    transport.handle(
        "resources/read",
        lambda p: {
            "contents": [{"uri": p["uri"], "mimeType": "text/plain", "text": f"body:{p['uri']}"}]
        },
    )
    transport.handle(
        "prompts/get",
        lambda p: {
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": f"prompt:{p['name']}:{p.get('arguments', {})}"},
                }
            ]
        },
    )
    return transport


def test_connect_sends_initialize_and_lists_tools() -> None:
    transport = _echo_server()
    client = McpClient(transport)
    client.connect()
    methods = [name for name, _ in transport.calls]
    assert methods[:3] == ["initialize", "notifications/initialized", "tools/list"]
    assert "echo" in client.list_tools()
    assert "list_issues" in client.list_tools()
    client.close()


def test_tool_call_returns_live_result_and_hits_tools_call() -> None:
    transport = _echo_server()
    with McpClient(transport) as client:
        result = client.echo(text="hi")
        assert isinstance(result, McpResult)
        assert result.text == "hi"
        assert result.content[0]["text"] == "hi"
        assert result.is_error is False
        assert any(name == "tools/call" and params["name"] == "echo" for name, params in transport.calls)


def test_hyphenated_tool_is_slugified() -> None:
    transport = _echo_server()
    with McpClient(transport) as client:
        assert client.list_issues().text == "ok"


def test_unknown_tool_raises() -> None:
    transport = _echo_server()
    with McpClient(transport) as client:
        with pytest.raises(McpError, match="unknown"):
            client.not_a_tool()


def test_tools_call_is_error_raises() -> None:
    transport = _echo_server()
    transport.handle("tools/list", lambda _p: {"tools": [{"name": "boom", "inputSchema": {"type": "object"}}]})
    transport.handle(
        "tools/call",
        lambda _p: {"content": [{"type": "text", "text": "fail"}], "isError": True},
    )
    with McpClient(transport) as client:
        with pytest.raises(McpError):
            client.boom()


def test_jsonrpc_error_raises() -> None:
    transport = FakeMcpTransport()
    transport.handle("initialize", lambda _p: (_ for _ in ()).throw(McpError("handshake failed")))
    client = McpClient(transport)
    with pytest.raises(McpError, match="handshake"):
        client.connect()


def test_read_resource_and_get_prompt() -> None:
    transport = _echo_server()
    with McpClient(transport) as client:
        listed = client.list_resources()
        assert listed == ["memo://1"]
        body = client.read_resource("memo://1")
        assert isinstance(body, McpResult)
        assert "body:memo://1" in body.text
        prompt = client.get_prompt("greet", who="ada")
        assert "prompt:greet" in prompt


def test_no_config_file_parser_in_library() -> None:
    import agentframe.mcp as pkg
    import inspect
    from pathlib import Path

    root = Path(inspect.getfile(pkg)).parent
    blob = "\n".join(p.read_text(encoding="utf-8") for p in root.glob("*.py"))
    assert "mcp.json" not in blob
    assert "claude_desktop_config" not in blob
