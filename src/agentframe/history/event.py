from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def new_tag() -> str:
    return uuid4().hex


@dataclass(frozen=True)
class Event:
    type: str
    payload: dict[str, Any]
    timestamp: datetime
    agent_id: str
    tag: str = field(default_factory=new_tag)

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            object.__setattr__(self, "timestamp", self.timestamp.replace(tzinfo=timezone.utc))
        if not self.tag:
            object.__setattr__(self, "tag", new_tag())
