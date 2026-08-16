# Phases

## Phase 1 — loop (this install)

`contracts`, `history`, `core`, `sandbox`, `runtime`.

Synchronous think → act → observe. In-process cells. In-memory events. Scripted E2E.

## Phase 2 — extras

- **`agentframe[mcp]`** — implemented. Consume MCP servers as composed objects (`self.github.create_issue(...)`). Fake, stdio, and Streamable HTTP transports. Design: spec §4.6 and §8.6.
- **`agentframe[rag]`** — implemented. Composed `Retriever` + `IngestionPipeline` + in-memory `VectorStore`. Never `Agent.retrieve()`.
- **`compose` extra implemented.** `compose()` assigns agents to fields; `Blackboard` is pub/sub over a caller-owned `EventLog`. No extra agent base class.

## Phase 3 — hardening

- **Pause/resume** — implemented. `AgentRuntime.iterate()` is a generator that yields `Paused` after a non-terminating CodeAct turn. Resume is `next()` on the same generator (same agent, same `EventLog`, same REPL locals). `run()` still drains to a validated return. Nested `_invoke` (calling an agentic method as a bound method) still runs to completion.
- **Isolated `Executor`** — implemented. `IsolatedExecutor` runs a cell in a child process (gVisor/`runsc` when present). Default-denies host filesystem and network. `InProcessExecutor` stays the loop default so pass-by-reference is unchanged. Isolated adapters do not claim live object identity.
- **Mutation testing** on `core` / `contracts` — not built.
