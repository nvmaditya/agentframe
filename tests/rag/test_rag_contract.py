"""Shared VectorStore / Retriever contract over every shipped adapter."""

from __future__ import annotations

import pytest

from agentframe.rag import Chunk, InMemoryVectorStore, Retriever, VectorStore


@pytest.fixture(params=[InMemoryVectorStore])
def store(request: pytest.FixtureRequest) -> VectorStore:
    return request.param()


def test_contract_empty_query(store: VectorStore) -> None:
    store.upsert([Chunk(text="hello world")])
    assert store.query("") == []


def test_contract_ingest_then_query(store: VectorStore) -> None:
    store.upsert([Chunk(text="red apple"), Chunk(text="blue ocean")])
    hits = Retriever(store).query("apple")
    assert [c.text for c in hits] == ["red apple"]


def test_contract_swap_store_changes_results() -> None:
    first = InMemoryVectorStore()
    second = InMemoryVectorStore()
    first.upsert([Chunk(text="alpha only")])
    second.upsert([Chunk(text="omega only")])
    assert Retriever(first).query("alpha")[0].text == "alpha only"
    assert Retriever(second).query("omega")[0].text == "omega only"
    assert Retriever(first).query("omega") == []
