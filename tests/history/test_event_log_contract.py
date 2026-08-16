"""Shared EventLog contract — every shipped adapter must pass this suite."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agentframe.history import Event, EventLog, InMemoryEventLog


def _event(type: str) -> Event:
    return Event(
        tag="",
        type=type,
        payload={},
        timestamp=datetime.now(timezone.utc),
        agent_id="contract",
    )


@pytest.fixture(params=[InMemoryEventLog])
def log(request: pytest.FixtureRequest) -> EventLog:
    return request.param()


def test_contract_append_query_roundtrip(log: EventLog) -> None:
    ev = log.append(_event("ModelTurn"))
    found = log.query(type="ModelTurn")
    assert found[-1].tag == ev.tag


def test_contract_collapse_keeps_originals_searchable(log: EventLog) -> None:
    a = log.append(_event("ModelTurn"))
    b = log.append(_event("Observation"))
    log.collapse(a.tag, b.tag, "summary")
    originals = [e for e in log.query(include_collapsed=True) if e.tag in {a.tag, b.tag}]
    assert len(originals) == 2
