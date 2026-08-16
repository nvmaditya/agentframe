"""Concrete in-memory adapter. runtime must not import this module."""

from __future__ import annotations

from agentframe.history.event import Event
from agentframe.history.log import EventLog


class InMemoryEventLog(EventLog):
    def __init__(self) -> None:
        self._events: list[Event] = []
        self._collapsed: set[str] = set()

    def append(self, event: Event) -> Event:
        self._events.append(event)
        return event

    def query(
        self,
        *,
        type: str | None = None,
        limit: int | None = None,
        include_collapsed: bool = True,
    ) -> list[Event]:
        items = list(self._events)
        if not include_collapsed:
            items = [e for e in items if e.tag not in self._collapsed]
        if type is not None:
            items = [e for e in items if e.type == type]
        if limit is not None:
            items = items[-limit:]
        return items

    def collapse(self, start_tag: str, end_tag: str, summary_text: str) -> Event:
        tags = [e.tag for e in self._events]
        try:
            start = tags.index(start_tag)
            end = tags.index(end_tag)
        except ValueError as exc:
            raise KeyError(f"unknown event tag in collapse({start_tag!r}, {end_tag!r})") from exc
        if end < start:
            start, end = end, start
        for ev in self._events[start : end + 1]:
            self._collapsed.add(ev.tag)
        summary = Event(
            type="Collapse",
            payload={
                "summary_text": summary_text,
                "start_tag": start_tag,
                "end_tag": end_tag,
            },
            timestamp=self._events[end].timestamp,
            agent_id=self._events[end].agent_id,
        )
        self._events.insert(end + 1, summary)
        return summary
