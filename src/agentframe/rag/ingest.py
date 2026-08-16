from __future__ import annotations

from agentframe.rag.chunk import Chunk
from agentframe.rag.store import VectorStore


class IngestionPipeline:
    """Write path. Separate from Retriever.query — ingest outside the agent turn."""

    def __init__(self, store: VectorStore) -> None:
        self.store = store

    def ingest(self, items: list[str] | list[Chunk]) -> None:
        chunks: list[Chunk] = []
        for item in items:
            if isinstance(item, Chunk):
                chunks.append(item)
            else:
                chunks.append(Chunk(text=item))
        self.store.upsert(chunks)
