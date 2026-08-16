from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentframe.history.event import Event
from agentframe.history.log import EventLog


class Blackboard:
    """Pub/sub over a caller-owned EventLog. Not a module singleton."""

    def __init__(self, events: EventLog, *, agent_id: str = "blackboard") -> None:
        self.events = events
        self.agent_id = agent_id

    def publish(self, type: str, payload: dict[str, Any] | None = None) -> Event:
        return self.events.append(
            Event(
                type=type,
                payload=payload or {},
                timestamp=datetime.now(timezone.utc),
                agent_id=self.agent_id,
            )
        )

    def query(self, type: str | None = None, limit: int | None = None) -> list[Event]:
        return self.events.query(type=type, limit=limit)
