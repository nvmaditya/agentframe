"""Short live multi-agent: manager CodeAct cell calls a composed worker."""

from __future__ import annotations

from agentframe import Agent, CodeActStrategy, strategy
from agentframe.compose import compose

try:
    from examples.ollama_runtime import ollama_runtime
except ImportError:  # python examples/ollama_team.py
    from ollama_runtime import ollama_runtime


class Worker(Agent):
    def shout(self, text: str) -> str:
        """Uppercase text."""
        return text.upper()


class Manager(Agent):
    """Delegate emphasis to the worker field. Do not reimplement shout."""

    @strategy(CodeActStrategy(max_turns=4))
    def run(self, task: str) -> str:
        """Call return_result(self.worker.shout(task)) and nothing else."""
        ...


def run_example() -> str:
    last: Exception | None = None
    for _ in range(2):
        try:
            return ollama_runtime().run(compose(Manager(), worker=Worker()), "hello")
        except Exception as exc:
            last = exc
    assert last is not None
    raise last


if __name__ == "__main__":
    print(run_example())
