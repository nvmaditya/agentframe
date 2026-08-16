"""Feature/E2E: scripted CodeAct cell queries a composed Retriever."""

from examples.rag_search import run_example


def test_rag_search_example() -> None:
    assert "cats" in run_example()
