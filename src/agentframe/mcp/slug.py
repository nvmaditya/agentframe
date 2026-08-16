from __future__ import annotations

import re


def slugify(name: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z_]", "_", name)
    if slug and slug[0].isdigit():
        slug = f"t_{slug}"
    if not slug:
        slug = "tool"
    return slug


def slugify_tools(names: list[str]) -> dict[str, str]:
    """Map original MCP tool names to unique Python identifiers."""
    used: set[str] = set()
    mapping: dict[str, str] = {}
    for original in names:
        base = slugify(original)
        candidate = base
        n = 2
        while candidate in used:
            candidate = f"{base}_{n}"
            n += 1
        used.add(candidate)
        mapping[original] = candidate
    return mapping
