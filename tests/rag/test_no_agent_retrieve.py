"""G5: retrieval is composed, never an Agent base method."""

from agentframe.core import Agent


def test_agent_has_no_retrieve_shortcut() -> None:
    assert not hasattr(Agent, "retrieve")
    assert "retrieve" not in getattr(Agent, "__agentframe_tools__", {})
