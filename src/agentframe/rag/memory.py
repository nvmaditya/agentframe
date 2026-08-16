from __future__ import annotations

from agentframe.rag.chunk import Chunk
from agentframe.rag.store import VectorStore


class InMemoryVectorStore(VectorStore):
    """In-process adapter. Substring match, no network, no embedding service."""

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    def upsert(self, chunks: list[Chunk]) -> None:
        self._chunks.extend(chunks)

    def query(self, text: str, limit: int = 5) -> list[Chunk]:
        needle = text.strip().lower()
        if not needle:
            return []
        hits = [chunk for chunk in self._chunks if needle in chunk.text.lower()]
        return hits[:limit]
