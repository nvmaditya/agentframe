"""Canonical example: a bad return_result is rejected and the loop continues."""

from __future__ import annotations

from agentframe import Agent, AgentRuntime, InMemoryEventLog, InProcessExecutor, ScriptedModelClient


class Greeter(Agent):
    """Greet someone, using shout for emphasis."""

    def shout(self, text: str) -> str:
        """Uppercase text."""
        return text.upper()

    def run(self, who: str) -> str:
        """Return a greeting string."""
        ...


def run_example() -> str:
    events = InMemoryEventLog()
    runtime = AgentRuntime(
        model=ScriptedModelClient(
            [
                "return_result(1)",
                "return_result(self.shout('hello ' + who))",
            ]
        ),
        executor=InProcessExecutor(),
        events=events,
    )
    value = runtime.run(Greeter(), "ada")
    if not events.query(type="ValidationError"):
        raise AssertionError("expected a ValidationError event before success")
    return value


if __name__ == "__main__":
    print(run_example())
