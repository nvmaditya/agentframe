from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class McpResult:
    text: str
    content: list[Any] = field(default_factory=list)
    is_error: bool = False