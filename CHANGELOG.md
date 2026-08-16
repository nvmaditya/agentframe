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
