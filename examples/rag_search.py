"""Canonical example: CodeAct queries a composed Retriever field."""

from __future__ import annotations

from agentframe import Agent, AgentRuntime, InMemoryEventLog, InProcessExecutor, ScriptedModelClient
from agentframe.rag import IngestionPipeline, InMemoryVectorStore, Retriever


class SearchAgent(Agent):
    """Answer using the retriever field."""

    rag: Retriever

    def run(self, task: str) -> str:
        """Return the first hit text for the task."""
        ...


def run_example() -> str:
    store = InMemoryVectorStore()
    IngestionPipeline(store).ingest(
        [
            "cats purr when content",
            "quantum physics lecture notes",
        ]
    )
    retriever = Retriever(store)
    runtime = AgentRuntime(
        model=ScriptedModelClient(
            ["hits = self.rag.query('cats')\nreturn_result(hits[0].text)"]
        ),
        executor=InProcessExecutor(),
        events=InMemoryEventLog(),
    )
    return runtime.run(SearchAgent(rag=retriever), "cats")


if __name__ == "__main__":
    print(run_example())
