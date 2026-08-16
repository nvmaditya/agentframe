from __future__ import annotations

from abc import ABC, abstractmethod

from agentframe.history.event import Event


class EventLog(ABC):
    @abstractmethod
    def append(self, event: Event) -> Event:
        """Append ``event`` and return the stored event (tag filled if empty)."""

    @abstractmethod
    def query(
        self,
        *,
        type: str | None = None,
        limit: int | None = None,
        include_collapsed: bool = True,
    ) -> list[Event]:
        """Chronological events. ``limit`` is the last N matches."""

    @abstractmethod
    def collapse(self, start_tag: str, end_tag: str, summary_text: str) -> Event:
        """Insert a Collapse event. Default rendering hides the closed range."""
