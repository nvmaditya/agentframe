"""Canonical example: CodeAct calls a composed MCP client field."""

from __future__ import annotations

from agentframe import Agent, AgentRuntime, InMemoryEventLog, InProcessExecutor, ScriptedModelClient
from agentframe.mcp import FakeMcpTransport, McpClient


def echo_transport() -> FakeMcpTransport:
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
                    "inputSchema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                }
            ]
        },
    )
    transport.handle(
        "tools/call",
        lambda p: {
            "content": [{"type": "text", "text": (p.get("arguments") or {}).get("text", "")}],
            "isError": False,
        },
    )
    return transport


class EchoAgent(Agent):
    """Call the echo tool on the attached MCP server."""

    server: McpClient

    def run(self, task: str) -> str:
        """Return the echo tool's text."""
        ...


def run_example() -> str:
    transport = echo_transport()
    client = McpClient(transport)
    client.connect()
    runtime = AgentRuntime(
        model=ScriptedModelClient(["return_result(self.server.echo(text='hi').text)"]),
        executor=InProcessExecutor(),
        events=InMemoryEventLog(),
    )
    value = runtime.run(EchoAgent(server=client), "echo")
    client.close()
    if not any(name == "tools/call" for name, _ in transport.calls):
        raise AssertionError("tools/call never happened")
    return value


if __name__ == "__main__":
    print(run_example())
