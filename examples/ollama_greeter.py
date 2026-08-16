"""Short live agent: CodeAct greeter against a local Ollama model."""

from __future__ import annotations

from agentframe import Agent, CodeActStrategy, strategy

try:
    from examples.ollama_runtime import ollama_runtime
except ImportError:  # python examples/ollama_greeter.py
    from ollama_runtime import ollama_runtime


class Greeter(Agent):
    """Greet people. Use shout when you want emphasis."""

    def shout(self, text: str) -> str:
        """Return text in uppercase."""
        return text.upper()

    @strategy(CodeActStrategy(max_turns=4))
    def greet(self, text: str) -> str:
        """Call return_result(self.shout(text))."""
        ...


def run_example() -> str:
    last: Exception | None = None
    for _ in range(2):
        try:
            return ollama_runtime().run(Greeter(), "hello ada", method="greet")
        except Exception as exc:
            last = exc
    assert last is not None
    raise last


if __name__ == "__main__":
    print(run_example())
