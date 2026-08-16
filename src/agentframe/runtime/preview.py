from __future__ import annotations

from typing import Any

PER_VALUE_CAP = 2048


def preview(name: str, value: Any, cap: int = PER_VALUE_CAP) -> str:
    """Bounded preview. Live object is never truncated."""
    if isinstance(value, (list, tuple)):
        kind = type(value).__name__
        length = len(value)
        head = list(value[:5])
        parts = [f"{name} = {kind}(len={length}", f"[:5]={head!r}"]
        if length > 5:
            parts.append(f"[-5:]={list(value[-5:])!r}")
        text = ", ".join(parts) + ")"
        return _clip(text, cap)
    text = f"{name} = {type(value).__name__}({value!r})"
    if len(text) <= 512:
        return _clip(text, cap)
    return _clip(f"{name} = {type(value).__name__}(len={len(str(value))}, head={str(value)[:40]!r})", cap)


def _clip(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    return text[: cap - 3] + "..."
