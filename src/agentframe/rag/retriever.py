from __future__ import annotations

from agentframe.rag.chunk import Chunk
from agentframe.rag.store import VectorStore


class Retriever:
    """Read path. Host constructs this and assigns it to an agent field."""

    def __init__(self, store: VectorStore) -> None:
        self.store = store

    def query(self, text: str, limit: int = 5) -> list[Chunk]:
        return self.store.query(text, limit=limit)
