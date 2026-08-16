"""InMemoryEventLog is append-only, queryable, and collapse-safe."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agentframe.history import Event, EventLog, InMemoryEventLog


def _event(type: str, payload: dict | None = None, agent_id: str = "a") -> Event:
    return Event(
        tag="",  # assigned by the log on append if empty
        type=type,
        payload=payload or {},
        timestamp=datetime.now(timezone.utc),
        agent_id=agent_id,
    )


def test_append_assigns_unique_tags_and_preserves_order() -> None:
    log: EventLog = InMemoryEventLog()
    first = log.append(_event("ModelTurn", {"n": 1}))
    second = log.append(_event("Observation", {"n": 2}))
    assert first.tag
    assert second.tag
    assert first.tag != second.tag
    assert [e.type for e in log.query()] == ["ModelTurn", "Observation"]


def test_query_filters_by_type_and_limit() -> None:
    log = InMemoryEventLog()
    for i in range(5):
        log.append(_event("ModelTurn", {"i": i}))
        log.append(_event("Observation", {"i": i}))
    turns = log.query(type="ModelTurn", limit=2)
    assert [e.payload["i"] for e in turns] == [3, 4]
    assert all(e.type == "ModelTurn" for e in turns)


def test_collapse_hides_range_from_default_render_query() -> None:
    log = InMemoryEventLog()
    a = log.append(_event("ModelTurn"))
    b = log.append(_event("Observation"))
    c = log.append(_event("ModelTurn"))
    summary = log.collapse(a.tag, b.tag, "two turns")
    assert summary.type == "Collapse"
    assert summary.payload["summary_text"] == "two turns"

    visible = log.query(include_collapsed=False)
    types = [e.type for e in visible]
    assert types == ["Collapse", "ModelTurn"]
    assert visible[-1].tag == c.tag

    all_events = log.query(include_collapsed=True)
    assert {e.tag for e in all_events} >= {a.tag, b.tag, c.tag, summary.tag}


def test_collapse_unknown_tag_raises() -> None:
    log = InMemoryEventLog()
    e = log.append(_event("ModelTurn"))
    with pytest.raises(KeyError):
        log.collapse("missing", e.tag, "nope")


def test_event_is_timezone_aware() -> None:
    log = InMemoryEventLog()
    ev = log.append(_event("TaskStarted"))
    assert ev.timestamp.tzinfo is not None


def test_naive_timestamp_is_marked_utc() -> None:
    ev = Event(
        type="ModelTurn",
        payload={},
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        agent_id="a",
    )
    assert ev.timestamp.tzinfo is not None


def test_collapse_swaps_reversed_tags() -> None:
    log = InMemoryEventLog()
    a = log.append(_event("ModelTurn"))
    b = log.append(_event("Observation"))
    log.collapse(b.tag, a.tag, "reversed")
    visible = log.query(include_collapsed=False)
    assert [e.type for e in visible] == ["Collapse"]
