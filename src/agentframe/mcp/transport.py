from __future__ import annotations

from typing import Any, Protocol


class McpTransport(Protocol):
    def open(self) -> None: ...

    def close(self) -> None: ...

    def request(self, method: str, params: dict[str, Any]) -> Any: ...