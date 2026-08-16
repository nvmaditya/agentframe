from __future__ import annotations

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    text: str
    id: str | None = None
    metadata: dict = Field(default_factory=dict)
