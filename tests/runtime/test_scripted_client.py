import pytest

from agentframe.runtime import ModelMessage, ScriptExhausted, ScriptedModelClient


def test_scripted_client_returns_turns_then_raises() -> None:
    client = ScriptedModelClient(["one", "two"])
    first = client.complete([ModelMessage(role="user", content="q")])
    assert first.content == "one"
    second = client.complete([ModelMessage(role="user", content="q")])
    assert second.content == "two"
    with pytest.raises(ScriptExhausted):
        client.complete([ModelMessage(role="user", content="q")])
