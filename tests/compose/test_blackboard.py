"""Blackboard is pub/sub over a caller-owned EventLog."""

from __future__ import annotations

from agentframe.compose import Blackboard
from agentframe.history import InMemoryEventLog


def test_publish_then_query_sees_the_event() -> None:
    log = InMemoryEventLog()
    board = Blackboard(log)
    published = board.publish("Note", {"text": "hello"})
    found = board.query(type="Note")
    assert found[-1].tag == published.tag
    assert found[-1].payload["text"] == "hello"


def test_no_match_is_empty() -> None:
    board = Blackboard(InMemoryEventLog())
    assert board.query(type="Missing") == []


def test_two_boards_do_not_share_a_log() -> None:
    a = Blackboard(InMemoryEventLog())
    b = Blackboard(InMemoryEventLog())
    a.publish("Note", {"text": "only-a"})
    assert b.query(type="Note") == []
    assert a.query(type="Note")[0].payload["text"] == "only-a"
