"""In-memory VectorStore: ingest, query, empty hits, swappable backend."""

from __future__ import annotations

from agentframe.rag import Chunk, InMemoryVectorStore, IngestionPipeline, Retriever, VectorStore


def test_empty_query_returns_no_hits() -> None:
    store: VectorStore = InMemoryVectorStore()
    store.upsert([Chunk(text="the cat sat")])
    assert store.query("") == []
    assert store.query("   ") == []


def test_ingest_then_query_returns_matching_chunk_only() -> None:
    store = InMemoryVectorStore()
    cat = Chunk(text="the cat sat on the mat", id="cat")
    physics = Chunk(text="quantum physics lecture notes", id="q")
    store.upsert([cat, physics])
    hits = store.query("cat")
    texts = [c.text for c in hits]
    assert "the cat sat on the mat" in texts
    assert "quantum physics lecture notes" not in texts


def test_pipeline_ingest_is_separate_from_query() -> None:
    store = InMemoryVectorStore()
    pipeline = IngestionPipeline(store)
    pipeline.ingest(["alpha document about apples", "beta document about boats"])
    retriever = Retriever(store)
    hits = retriever.query("apples")
    assert any("apples" in c.text for c in hits)
    assert all("boats" not in c.text for c in hits)


def test_swapping_store_changes_what_is_retrieved() -> None:
    a = InMemoryVectorStore()
    b = InMemoryVectorStore()
    IngestionPipeline(a).ingest(["only in store a: zebras"])
    IngestionPipeline(b).ingest(["only in store b: penguins"])
    retriever = Retriever(a)
    assert any("zebras" in c.text for c in retriever.query("zebras"))
    assert retriever.query("penguins") == []
    retriever = Retriever(b)
    assert any("penguins" in c.text for c in retriever.query("penguins"))
    assert retriever.query("zebras") == []
