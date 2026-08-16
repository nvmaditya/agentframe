# Agentic Framework (OOP-Native) — Product Requirements Document

> **Document type**: PRD
> **Status**: Draft (for review)
> **One-line summary**: A small Python framework where agents are plain objects — state is fields, tools are methods, prompts are docstrings, contracts are type hints, and workflows are ordinary control flow.

---

## 1. Problem Statement

Existing agent frameworks (LangGraph, CrewAI, AutoGen) impose a parallel mental model on top of Python — graphs, nodes, edges, YAML-ish config — for things that Python already has native primitives for. This adds a learning curve, debugging pain (stack traces through framework internals), and indirection for small-to-medium agent projects that don't need distributed graph execution.

This framework's bet: **if you map every agentic concept to an existing OOP/Python primitive, you get an agent framework that is debuggable with `pdb`, testable with `pytest` like any other Python code, and has zero bespoke DSL to learn.**

## 2. Goals

- **G1 — Native mapping.** Every core agentic concept (state, tools, prompts, contracts, memory, workflow, multi-agent, actions, execution, history) maps to an existing Python/OOP primitive. No new syntax invented where Python already has an answer.
- **G2 — Full modularity.** Every module (Agent core, Tool system, Contracts, Memory, Runtime, Multi-agent composition, Sandbox executor, Event log, RAG) is independently installable, testable, and replaceable without touching other modules' internals.
- **G3 — Test-gated releases.** Nothing ships — not even a minor version — without unit, integration, feature/e2e, and contract tests passing at defined coverage thresholds.
- **G4 — Code-as-action.** Agents act by writing Python code (à la smolagents' CodeAgent), not chained JSON tool calls, executed in a sandboxed boundary.
- **G5 — Pluggable RAG.** Retrieval is a composed object, not baked into the Agent base class; backend (Qdrant/Neo4j/pgvector/etc.) is swappable behind one interface.

## 3. Non-Goals

- **Not** a distributed/multi-node execution engine (no built-in Ray/Celery orchestration in v1).
- **Not** a low-code/no-code builder — this is a code-first framework for engineers, not a GUI.
- **Not** attempting to support every LLM provider on day one — start with an Anthropic/OpenAI-compatible client interface, generalize later.
- **Not** a hosted product — this ships as a pip-installable library, not a SaaS.

## 4. Target User

Solo builders and small teams (2–5 engineers) who want agent behavior in an existing Python codebase without adopting a framework-specific mental model. Primary use case: internal tools, research agents, and RAG-backed assistants where debuggability matters more than horizontal scale.

---

## 5. Core Concept Map (Design Contract)

This table **is** the spec. Every module below must honor it — if a module can't be explained in terms of this table, it doesn't belong in the framework.

| Concept | Python/OOP Primitive |
|---|---|
| Agent | Object (instance of `Agent` or subclass) |
| State | Instance fields (`self.__dict__`) |
| Tools | Methods decorated with `@tool` |
| Prompt | Docstrings (class + method level) |
| Contracts | Type annotations (Pydantic models / dataclasses) |
| Memory | Object state + `MemoryAPI` (short-term) / pluggable store (long-term) |
| Workflow | Python control flow (`if`/`for`/`while`, generators for pause/resume) |
| Multi-agent | Object composition (agents as fields of other agents) |
| Actions | Generated Python code, executed in a sandboxed subprocess |
| Execution | `AgentRuntime` (the think → act → observe loop) |
| History | Append-only `Event` log |
| Retrieval (RAG) | Composed `Retriever` object exposed as a tool |

**Precedent**: this concept map is not just plausible — NVIDIA's NOOA framework (`NVIDIA-NeMo/labs-OO-Agents`, arXiv:2607.20709) implements a near-identical mapping and reports 82.2% on SWE-bench Verified and 86.8% on CyberGym L1. Several of its concrete mechanisms are adopted below rather than reinvented; each is marked **[NOOA]**.

---

## 6. Module Breakdown

Each module ships as its own installable extra (`pip install agentframe[rag]`, `agentframe[sandbox]`, etc.) and must satisfy: **no module imports a concrete implementation of another module — only its interface.**

### 6.1 `core` — Agent base class
- **Owns**: `Agent` base class, docstring-to-prompt extraction, `__init__` state binding.
- **Method convention [NOOA]**: a method whose body is a real Python implementation is deterministic — callable by the model as a tool, testable and debuggable like any function. A method whose body is the ellipsis literal (`...`) is *agentic* — the runtime completes it via an LLM-driven loop at call time. This replaces a separate `@tool` decorator with a convention already legible to any Python developer: the body itself declares what the method is.
- **Model-facing surface exclusion**: a leading underscore excludes a method from the model-callable surface, matching Python's own convention for "internal." `_validate_state(self)` is callable from other methods but never offered to the model as a tool; only public real-body methods are. This prevents every implementation-detail method from silently becoming agent-callable just because `@tool` no longer gates it.
- **Strategy pattern [NOOA]**: agentic methods are further annotated with `@strategy(...)`, which controls *how* the loop runs without changing the method's ordinary signature or typed boundary:
  - `PredictStrategy` — a single typed LLM call with local retry-on-validation-failure. Use for classification/extraction where the model doesn't need to inspect state.
  - `CodeActStrategy` (default) — an iterative Python REPL loop: the model can call `execute_python(...)` to inspect state, call helper methods, or invoke other agentic methods, then terminate with `return_result(...)`, type-validated before it's accepted.
- **Public interface**: `Agent`, `strategy()`, `PredictStrategy`, `CodeActStrategy`.
- **Depends on**: nothing (stdlib + `inspect` only).
- **Must not depend on**: runtime, sandbox, memory, RAG. Core has to work with zero optional extras installed.

### 6.2 `contracts` — Type/schema layer
- **Owns**: conversion of type hints → JSON schema for tool calling; Pydantic model validation on tool inputs/outputs.
- **Public interface**: `schema_from_signature()`, `validate_output()`.
- **Depends on**: `pydantic` (pinned, only external hard dependency of the whole framework).

### 6.3 `memory` — Short + long-term memory
- **Owns**: `MemoryAPI` interface (`.query(text) -> list[Item]`, `.write(item)`), in-object working memory, pluggable persistent backends (SQLite default, others via adapter).
- **Two recall channels [NOOA]**: memory is not a single flat store the runtime silently manages. It's writable and readable through two distinct paths:
  - **Deliberate recall** — the agent calls explicit tools (`remember`, `recall`, `search`, `update_memory`, `forget`) as its own choice, same as any other tool call. Writing a memory is a decision the model makes, not a background extraction step — this keeps memory quality tied to what the agent judged worth keeping.
  - **Spontaneous recall** — a `BeforeTurn` hook derives a query from recent events and injects associated memories into a dynamic context block automatically, without the model asking. Injected memories should not be double-counted as "used" just because they were surfaced, to avoid distorting which memories look valuable.
- **Consolidation runs outside the loop**: a separate, non-blocking pass (after a task completes or while idle) merges near-duplicates, resolves conflicting values, and prunes low-value/decayed entries — never touching this synchronously inside an agent's turn, so memory upkeep doesn't cost the user latency.
- **One inspectable store**: default backend is a single SQLite file a developer can open directly; vector indexes are derived and swappable, not the source of truth.
- **Public interface**: `Memory`, `MemoryBackend` (ABC).
- **Depends on**: `core` interface only, not `core` internals.
- **Note**: shares the same `.query()/.write()` shape as `Retriever` deliberately (see §6.7) — not the same class, but same protocol, so they're composable later without a rewrite.

### 6.4 `sandbox` — Action execution
- **Owns**: execution of model-generated code, timeout enforcement, resource limits, captured stdout/return value marshaling back to the agent.
- **Decision: in-process execution, not subprocess-per-action.** Code runs in the same process as the agent, against live objects — this is what makes pass-by-reference (§6.5) possible at all; subprocess isolation would mean serialized copies at the boundary, killing the live-object benefit that's the actual point of G4. Safety comes from rejecting dangerous builtins (`eval`, `exec`, `compile`, `input`, blocking event-loop calls) at the interpreter level, plus an *external* process/container/VM boundary around the whole agent — a deployment-layer concern, not something `sandbox` re-implements per call. This module protects the agent loop; the deployment protects the host. Phase 1 ships the interpreter-level restrictions only; a container/gVisor-hardened `Executor` is explicitly Phase 3 (§10).
- **Public interface**: `Executor` (ABC), `InProcessExecutor` (default and only Phase 1 impl).
- **Depends on**: nothing from other modules — takes a string of code and a tool registry, returns a result.

### 6.5 `runtime` — AgentRuntime (the loop)
- **Owns**: think → act → observe loop, streaming, resume-from-history, orchestrates calls to `sandbox` and appends to `history`.
- **Pass-by-reference, not copy-as-text [NOOA]**: arguments and tool results are bound as live Python locals in the execution namespace; only a bounded preview (type, true length, head/tail sample — e.g. `records = list(len=100, [:5]=[...], [-5:]=[...])`) is rendered into the model's context. The variable itself is never truncated. This is what lets an agent process a multi-million-row table by writing code against it, while the prompt only ever carries a fixed-size preview — the amount of data an agent can process is bounded by the execution environment, not by the prompt. This is a hard requirement for `runtime`, not a nice-to-have: it's the mechanism that makes G4 (code-as-action) actually pay off instead of just being a stylistic choice.
- **Three-region context rendering [NOOA]**: for cache efficiency, context is assembled from three sources — a static prefix (system prompt, docstring-derived instructions; unchanged across turns, cacheable), the event history (append-only, grows only by appending), and dynamic blocks (todo status, live state summaries; re-evaluated every turn, placed at the tail). Keeping static content first and volatile content last maximizes KV-cache reuse turn over turn.
- **Validated termination**: an agentic method only returns when its result passes the declared return-type contract (Pydantic validation); a failed validation sends the model an error and the loop continues. This closes a known failure mode in other harnesses — models declaring "done" without meeting the actual contract — by making termination a programmatically validated action, not an informal convention in the prompt.
- **Public interface**: `AgentRuntime.run(agent, task) -> Result`.
- **Depends on**: `core`, `sandbox` (interface, not impl), `history` (interface, not impl).

### 6.6 `history` — Event log
- **Owns**: append-only `Event` model (`type`, `payload`, `timestamp`, `agent_id`), in-memory + pluggable persistent sink (file/SQLite/Postgres).
- **Queryable, not just appendable [NOOA]**: each event is a typed object with a unique tag, exposed through a Pythonic API usable by both developer and agent — e.g. `self.events.query(type="ToolCall", limit=3)` to pull recent events by kind, and `self.events.collapse(start_tag, end_tag, summary_text=...)` to compact a long stretch of history into a summary event while keeping it searchable afterward. This turns History from a passive audit log into an active part of the agent's own working interface — an agent can inspect its own recent actions programmatically instead of re-reading a flat transcript.
- **Public interface**: `Event`, `EventLog` (ABC), `InMemoryEventLog` (default), `EventLog.query()`, `EventLog.collapse()`.
- **Depends on**: nothing.

### 6.7 `rag` (optional extra) — Retrieval
- **Owns**: `Retriever` object, `IngestionPipeline` (separate lifecycle from retrieval — see prior design discussion), reranker/HyDE as swappable sub-components.
- **Public interface**: `Retriever`, `VectorStore` (ABC — Qdrant/pgvector/Neo4j adapters live behind this), `Chunk` (Pydantic model).
- **Depends on**: `contracts` (for `Chunk` schema), exposed to `core` only as a `@tool`-wrapped method — `rag` never imports `core`, `core`/user code imports `rag` and wraps it.
- **Removable test**: the framework must run its full test suite with `rag` extra *not installed* and nothing else breaks. This is the hard modularity gate for this module.

### 6.8 `compose` — Multi-agent
- **Owns**: patterns for agent-as-field composition (manager/worker), plus a thin pub/sub helper over `history` for blackboard-style non-hierarchical patterns.
- **Public interface**: `compose()` helper, no required base class — composition is just "assign an Agent to a field," reinforcing G1.
- **Depends on**: `core`, `history` interface.

---

## 7. Modularity Requirements (Hard Requirements, Not Aspirations)

1. **Interface-only cross-module imports.** A module may import another module's ABC/Protocol, never its concrete class. Enforced via a lint rule / import-linter contract in CI (e.g., `import-linter` with layered contracts).
2. **Every module installable and testable in isolation.** `pip install agentframe` (core only) must pass its own test suite with zero optional extras present.
3. **No global mutable state.** No module-level singletons for registries, event logs, or memory stores — everything is instance-owned and passed explicitly. This is what makes multi-agent composition (§6.8) safe.
4. **Versioned internal interfaces.** ABCs in `memory`, `history`, `sandbox`, and `rag` are treated as a semver'd internal API — breaking an ABC signature is a major-version bump for the framework, not a patch.
5. **Dependency injection over configuration files.** Swapping a vector store or executor backend happens by passing a different object into a constructor, never through a YAML/JSON config the framework parses. Keeps the "it's just Python" promise from §G1.

---

## 8. Testing Requirements (Release Gate)

**No module, feature, or version ships until all four tiers below pass in CI.** This is a hard gate, not a goal — a red pipeline blocks merge to `main` and blocks release, no exceptions for "small" changes.

| Tier | Scope | Tooling | Threshold |
|---|---|---|---|
| **Unit** | Single class/function in isolation, all dependencies mocked (e.g., `@tool` extraction logic, schema generation, `Event` serialization) | `pytest` + `pytest-mock` | ≥ 90% line coverage per module |
| **Integration** | Two or more real modules wired together (e.g., `runtime` + `sandbox` executing a real generated action; `rag` `Retriever` + real (test) vector store) | `pytest` with real lightweight backends (in-memory SQLite, local Qdrant test container) | All module-pair boundaries defined in §6 covered by ≥ 1 test |
| **Feature / E2E** | Full agent runs against a scripted scenario (given a task, agent produces expected tool calls / final answer within tolerance) | `pytest` + fixture agents + a deterministic/mocked LLM client for reproducibility | Every documented example in the README/docs must be a passing E2E test — docs can't drift from behavior |
| **Contract** | Verifies that every concrete backend (e.g., `InProcessExecutor`, SQLite `MemoryBackend`, Qdrant `VectorStore` adapter) actually satisfies its ABC's behavioral contract, not just its type signature | Shared contract test suite run against every implementation (`pytest` parametrized over implementations) | 100% of shipped backend implementations pass the shared contract suite |
| **Interface capability** [NOOA] | A distinct concern from the four tiers above: not "is the framework's code correct," but "can a target LLM correctly *use* the framework's model-facing primitives" — typed method calls, structured returns, stateful object manipulation, REPL/code execution, error recovery, context/truncation handling, task decomposition into helper calls | Small, focused scenarios (1–5 turns each), one interface behavior isolated per test; run against real or recorded model calls | Run each scenario **5× per supported model** to separate two failure modes: a scenario that fails all 5 runs signals the interface itself doesn't work; a scenario that fails intermittently signals a reliability gap worth tracking but not necessarily blocking. Track both rates separately rather than collapsing to one pass/fail number. |

**Additional gates:**
- **Modularity gate**: CI job that installs `core` alone and runs its test suite with `rag`, `sandbox`-hardened, and `compose` extras absent — must pass clean.
- **Security gate on `sandbox`**: adversarial test cases (attempted filesystem escape, network access, fork bombs, infinite loops) must be caught by timeout/resource limits before this module can be marked stable.
- **Mutation testing (stretch, not v1-blocking)**: `mutmut` or similar on `core` and `contracts` given their blast radius if broken.

### Definition of Done (per module, per PR)
- [ ] Unit tests written and passing, coverage threshold met
- [ ] If module touches ≥1 other module's interface: integration test added
- [ ] If module is user-facing (appears in a documented example): E2E test added or updated
- [ ] If module ships a new backend implementation: contract test passes
- [ ] Import-linter contract updated/passing (no illegal cross-module concrete imports)
- [ ] Docs/README examples updated to match, and those examples are themselves tests (per Feature tier above)

---

## 9. Non-Functional Requirements

- **Debuggability**: any agent run must be steppable in `pdb`/breakpoints without special tooling — a direct consequence of "workflow = control flow."
- **Observability**: every tool call, retrieval, and action execution is a `history.Event` by default, no opt-in required.
- **Security boundary**: `sandbox` execution must never have filesystem/network access beyond an explicit allowlist passed by the host application.
- **Latency**: framework overhead (schema generation, event logging, tool dispatch) should add negligible latency versus raw LLM call time — no hidden network calls inside `core`/`contracts`.

---

## 10. Phasing

**Phase 1 (MVP, ~4–6 weeks)**
- `core`, `contracts`, `history`, minimal `runtime` (synchronous think→act→observe only, no pause/resume)
- `sandbox` with subprocess isolation (not container-hardened yet)
- Unit + integration test tiers fully wired into CI; feature/E2E tier covering at least 3 canonical example agents
- No `rag`, no `compose` yet — ship the skeleton with the modularity gate proven first

**Phase 2**
- `rag` extra (Retriever, IngestionPipeline, one vector store adapter — Qdrant, given prior familiarity)
- `compose` extra (manager/worker pattern + blackboard-over-history helper)
- Contract test tier stood up across all shipped backends

**Phase 3**
- Async/generator-based pause-resume in `runtime` (for human-in-the-loop and fan-out/fan-in workflows)
- Hardened sandbox (container/gVisor-backed `Executor`)
- Mutation testing on `core`/`contracts`

---

## 11. Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Sandbox escape from model-generated code | Ship `sandbox` with a restrictive default (no network/filesystem by default) and a dedicated adversarial test suite before calling it stable; don't let feature velocity outpace this module's hardening |
| In-process execution (§6.4, option A) means a validator bug is a host compromise, not just an agent-loop bug | Explicit in the design, not hidden: treat process/container-level isolation as a mandatory deployment requirement documented and tested separately from `sandbox`'s own interpreter-level restrictions — the module protects the agent loop, the deployment protects the host |
| Modularity erodes over time as convenience shortcuts creep in (`core` quietly importing `rag` for a "nice default") | Enforce via CI import-linter contract, not code review discipline alone — discipline doesn't scale, tooling does |
| Test-gate slows early iteration to a crawl | Keep Phase 1 scope small (5 modules: core, contracts, history, runtime, sandbox) specifically so the full 4-tier suite is cheap to run; expand test surface area at the same rate as module surface area, not ahead of it |
| "Workflow = control flow" breaks down for fan-out/fan-in and human-in-the-loop | Explicitly deferred to Phase 3 with generators/async — documented as a known v1 limitation rather than papered over |
| RAG module coupling creeps into `core` for convenience (e.g., `Agent.retrieve()` shortcut) | Keep `rag` strictly tool-composed (§6.7) — the "removable test" (full suite green with `rag` uninstalled) is the enforcement mechanism |

## 12. Resolved Decisions

- **Decision: minimal internal `ModelClient` protocol, not `litellm`.** Keeps the dependency surface small and matches the "it's just Python, no bespoke abstraction where one isn't needed" ethos — trades provider-adapter breadth for full control over the request/response shape the runtime depends on. Anthropic/OpenAI-compatible clients are hand-written adapters against this protocol.
- **Decision: `history` stays in-memory only in Phase 1.** Durable persistence (SQLite or otherwise) is deferred until a real use case needs to survive process restarts — avoids building storage-layer complexity ahead of demonstrated need.
- **Decision: scripted mock LLM for the Feature/E2E tier, not VCR-style cassettes.** This tier's job is to keep documented examples honest and catch harness-level regressions deterministically and fast — it is intentionally *not* where real-model behavior gets validated. That job belongs to the **Interface Capability tier** (§8), which runs against real or recorded model calls, 5× per model, specifically to measure whether actual LLMs can use the framework's primitives. The two tiers are complementary, not redundant: E2E tests "does the harness do what the docs say," Interface Capability tests "can a model actually drive this interface."
