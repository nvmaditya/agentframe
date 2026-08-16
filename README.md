# agentframe

Agents as objects. No graph, no YAML, no second language.

State is fields. Tools are methods. Prompts are docstrings. Contracts are type hints. The model acts by writing Python against live objects — the prompt only ever sees a bounded preview.

```python
from agentframe import Agent, AgentRuntime, InMemoryEventLog, InProcessExecutor
from agentframe import ScriptedModelClient

class Greeter(Agent):
    """Greet people. Use shout when you want emphasis."""

    name: str

    def shout(self, text: str) -> str:
        """Return text in uppercase."""
        return text.upper()

    def greet(self, who: str) -> str:
        """Greet `who` and return the greeting string."""
        ...

runtime = AgentRuntime(
    model=ScriptedModelClient(["return_result(self.shout('hello ' + who))"]),
    executor=InProcessExecutor(),
    events=InMemoryEventLog(),
)
print(runtime.run(Greeter(name="Ada"), "world", method="greet"))
# HELLO WORLD
```

That `...` body is the agentic method. A real body is just a function — callable by the model, testable with `pytest`, steppable in `pdb`.

## Install

```bash
pip install agentframe
```

Requires Python 3.11+. The only hard dependency is Pydantic v2.

## Status

Phase 1 of the loop is implemented: `core`, `contracts`, `history`, `sandbox`, `runtime`. MCP consume ships as `agentframe[mcp]` (`from agentframe.mcp import McpClient`). RAG and multi-agent helpers are specified and not in this install.

Documented examples live in [`examples/`](examples/) and are the Feature/E2E suite.

| | |
|---|---|
| Design | [`docs/superpowers/specs/2026-08-16-oop-native-agent-framework-design.md`](docs/superpowers/specs/2026-08-16-oop-native-agent-framework-design.md) |
| PRD | [`docs/prd.md`](docs/prd.md) |
| Phase 1 plan | [`docs/phase-1-plan.md`](docs/phase-1-plan.md) |
| Agent notes | [`AGENTS.md`](AGENTS.md) |

## Ideas, mapped

| You want | You write |
|---|---|
| Memory for this run | instance fields |
| A tool | a method with a real body |
| An LLM loop | a method whose body is `...` |
| How the loop runs | `@strategy(PredictStrategy())` or CodeAct (default) |
| A contract | a return annotation |
| An MCP server | a composed field (`McpClient` from `agentframe.mcp`) |

The model never gets a JSON tool list. It gets Python, and `return_result(value)` is accepted only when `value` passes the return type.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run lint-imports
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT.
