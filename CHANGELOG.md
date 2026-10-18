# Changelog

## 0.1.0 (unreleased)

Phase 1 of the OOP-native agent loop.

- `contracts` — `schema_from_signature`, `validate_output`
- `history` — `Event`, `EventLog`, `InMemoryEventLog`
- `core` — `Agent`, `strategy`, `PredictStrategy`, `CodeActStrategy`
- `sandbox` — `Executor`, `InProcessExecutor`
- `runtime` — `AgentRuntime`, `ModelClient`, `ScriptedModelClient`, `OpenAICompatibleClient`
- Feature/E2E examples in `examples/`, GitHub Actions CI, import-linter contracts
- Coverage measures the imported package (`source_pkgs`) so CI matches local runs
- `agentframe[mcp]` — consume MCP servers as composed objects (`McpClient`, fake / stdio / Streamable HTTP)
- `agentframe[rag]` — composed `Retriever`, `IngestionPipeline`, in-memory `VectorStore`
- `agentframe[compose]` — `compose()` field assignment and `Blackboard` over `EventLog`
- `AgentRuntime.iterate()` — generator pause/resume; yields `Paused` after a non-terminating CodeAct turn. `run()` still drains to a validated return
- CodeAct cells see public agent fields as bare names (`worker.shout(...)` as well as `self.worker.shout(...)`)
- `OpenAICompatibleClient` accepts optional `temperature`
- Live Ollama examples: `examples/ollama_greeter.py`, `examples/ollama_team.py`, `examples/ollama_helper.py`
- `IsolatedExecutor` — process-isolated cells (gVisor/`runsc` when present). Default-denies host FS and network. Direct cell runner only: `AgentRuntime` refuses an executor that does not keep the live object. `InProcessExecutor` is the loop executor.
