# Phases

## Phase 1 — loop (this install)

`contracts`, `history`, `core`, `sandbox`, `runtime`.

Synchronous think → act → observe. In-process cells. In-memory events. Scripted E2E.

## Phase 2 — extras (specified, not built)

- **`agentframe[mcp]`** — consume MCP servers as composed objects (`self.github.create_issue(...)`). Design: spec §4.6 and §8.6. Phase 1 already publishes methods on public fields so this extra does not rewrite `runtime`.
- **`agentframe[rag]`** — composed `Retriever`. Never `Agent.retrieve()`.
- **`compose`** — helpers for agent-as-field. Composition already works as ordinary assignment.

## Phase 3 — named only

Async / generator pause-resume, container/gVisor `Executor`, mutation testing on `core` and `contracts`.
