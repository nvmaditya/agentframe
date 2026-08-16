# Phases

## Phase 1 — loop (this install)

`contracts`, `history`, `core`, `sandbox`, `runtime`.

Synchronous think → act → observe. In-process cells. In-memory events. Scripted E2E.

## Phase 2 — extras

- **`agentframe[mcp]`** — implemented. Consume MCP servers as composed objects (`self.github.create_issue(...)`). Fake, stdio, and Streamable HTTP transports. Design: spec §4.6 and §8.6.
- **`agentframe[rag]`** — implemented. Composed `Retriever` + `IngestionPipeline` + in-memory `VectorStore`. Never `Agent.retrieve()`.
- **`compose`** — specified, not built. Helpers for agent-as-field. Composition already works as ordinary assignment.

## Phase 3 — named only

Async / generator pause-resume, container/gVisor `Executor`, mutation testing on `core` and `contracts`.
