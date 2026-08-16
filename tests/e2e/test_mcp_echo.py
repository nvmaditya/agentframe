"""Feature/E2E: scripted CodeAct cell calls a bound MCP tool."""

from examples.mcp_echo import run_example


def test_mcp_echo_example() -> None:
    assert run_example() == "hi"
