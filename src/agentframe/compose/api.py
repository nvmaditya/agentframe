from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


def compose(parent: T, **fields: Any) -> T:
    """Attach agents (or any objects) as fields. No extra base class."""
    for name, value in fields.items():
        setattr(parent, name, value)
    return parent
