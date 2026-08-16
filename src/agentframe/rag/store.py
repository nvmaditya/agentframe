from __future__ import annotations

from abc import ABC, abstractmethod

from agentframe.rag.chunk import Chunk


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: list[Chunk]) -> None:
        """Add or replace chunks. Ingest is not a retrieve-turn side effect."""

    @abstractmethod
    def query(self, text: str, limit: int = 5) -> list[Chunk]:
        """Return matching chunks, best first. Empty text → no hits."""
