# OOP-Native Agent Framework — Phase 1 Design Spec

**Date**: 2026-08-16
**Status**: Written for review (not an implementation plan)
**Source idea**: `agent-framework-prd.md`
**Scope of this document**: Phase 1 loop (`core`, `contracts`, `history`, `runtime`, `sandbox`) and the `mcp` extra’s interface (specified here; not in the Phase 1 install)

This spec turns the draft PRD into a buildable Phase 1 design. It records the approaches considered, the recommendation, and the decisions that the PRD left open or stated twice. Review added Model Context Protocol (MCP) as a first-class composed extra — consume servers as objects, not as a second tool-calling protocol. It is not a copy of the PRD and it is not an implementation.

---

## 1. Context

The product is a small Python library whose bet is: every agentic concept maps to an existing OOP/Python primitive, so an agent is debuggable with `pdb`, testable with `pytest`, and has no bespoke DSL.

The workspace today is the PRD plus this spec. There is no library package, no examples, and no test tree. This goal stops at the spec. Implementation starts only after this document is approved, via a later `writing-plans` pass.

The design adopts several mechanisms the PRD already marked **[NOOA]** (NVIDIA Object-Oriented Agents, arXiv:2607.20709): ellipsis-body agentic methods, `@strategy`, CodeAct vs Predict, pass-by-reference with bounded previews, three-region context, validated termination, and a queryable event log. It does not clone NOOA, match its benchmark numbers, or take on NOOA’s async/memory/container surface in Phase 1.

---

## 2. Phase 1 scope

Phase 1 is one implementation-plan-sized slice: a synchronous, in-process, code-as-action agent loop with typed contracts and an append-only event log.

**In Phase 1**

| Module | What it is responsible for |
|---|---|
| `core` | `Agent` base, docstring extraction, `__init__` field binding, method classification (deterministic vs agentic), `strategy()` / `PredictStrategy` / `CodeActStrategy` as declarations |
| `contracts` | `schema_from_signature()`, `validate_output()`; only hard third-party dependency (`pydantic`) |
| `history` | `Event`, `EventLog` interface, `InMemoryEventLog` with `query` and `collapse` |
| `runtime` | Synchronous think → act → observe; three-region rendering; pass-by-reference binding; validated termination; `AgentRuntime.run` |
| `sandbox` | `Executor` interface and `InProcessExecutor` (restricted in-process cells, timeout, stdout/display capture) |

**Out of this spec (named so they are not silently designed here)**

| Later slice | Why it is not Phase 1 |
|---|---|
| `memory` extra (deliberate/spontaneous recall, SQLite store, idle consolidation) | Working memory in Phase 1 is instance fields plus the event log. The MemoryAPI is a real module, not a stub. |
| `rag` extra (`Retriever`, ingestion, vector-store adapters) | Product goal G5, not this build. The removable-test rule is recorded so Phase 2 cannot leak into `core`. |
| `compose` extra (manager/worker helpers, blackboard-over-history) | Multi-agent in Phase 1 is ordinary object composition: assign an `Agent` to a field. No helper ships. |
| Generator / async pause-resume, streaming | Phase 1 `ModelClient.complete` and `AgentRuntime.run` are synchronous. |
| Container / gVisor / per-action subprocess `Executor` | Host isolation is a deployment concern. Per-action subprocess would break pass-by-reference. |
| Persistent event-log backends (SQLite/file/Postgres) | Default is in-memory until a durability need exists. |
| `litellm`, native Anthropic adapter, multimodal content | One `ModelClient` protocol + one OpenAI-compatible adapter. Text in, text out. |
| Record/replay (VCR) E2E and live interface-capability CI | Feature/E2E uses a scripted mock. Live-model fluency tests are a later, separate track. |
| Mutation testing | Stretch, not a Phase 1 gate. |
| `mcp` extra transports (stdio / Streamable HTTP) | Interface and composition seam are specified in §4.6 / §8.6. The extra is the first installable extra after the Phase 1 loop, not part of the base install. |

Phase 1 ships as a single distribution name **`agentframe`**. The first extra is **`agentframe[mcp]`**. Later extras (`agentframe[rag]`, `agentframe[compose]`, …) follow the same rule. G2’s interface-only and independently-testable rules apply now. Phase 1 still publishes methods on composed public fields (the seam `McpClient` will sit on) so the extra does not rewrite `runtime`.

---

## 3. Approaches considered

Three ways to cut Phase 1 were compared. Only Approach A keeps G1, G4, and pass-by-reference without adding a provider hub.

### Approach A — In-process CodeAct object framework (recommended)

Five Phase 1 modules, no new DSL. A method with a real body is a deterministic tool. A method whose body is `...` is agentic; `@strategy` selects Predict (one typed call) or CodeAct (REPL). Generated cells run in-process against live objects. The host injects a minimal `ModelClient`. History is in-memory. E2E tests drive a scripted client.

- **Pays off G1 and G4**: pass-by-reference and `pdb` on the same objects the model just touched.
- **Small dependency surface**: `pydantic` plus whatever the *host* already uses to talk to a model.
- **Testable without network**: the scripted client is a first-class `ModelClient` adapter.
- **Host safety is not the module’s job**: interpreter-level restrictions protect the agent loop; a compromised validator is a host compromise. That is explicit, not hidden.

### Approach B — Subprocess-per-action plus `@tool`

Keep the PRD’s §5 decorator and §10 “subprocess isolation.” Each model action is a child process. Tools are methods marked `@tool`. Results cross the process boundary as serialized copies.

- **Stronger per-call isolation** (a runaway cell dies with the child).
- **Breaks the hard runtime requirement**: no live references, so a 100k-row table must be copied or preview-only. Code-as-action becomes a style, not a way to process data larger than the prompt.
- **Two ways to mark tools** (`@tool` and “has a real body”) for no gain.
- **Harder `pdb`**: the interesting execution is in another process.

### Approach C — Provider hub plus durable log from day one

Depend on `litellm` (or similar) for every vendor, default history to SQLite, and validate E2E with VCR cassettes of real model traffic.

- **Broader provider coverage and durable traces immediately.**
- **Takes a large dependency** the PRD’s non-goals told us not to start with.
- **Cassettes couple tests to prompt wording** and fail opaquely when rendering changes.
- **Does not decide the sandbox/strategy contradictions**; it only adds surface area.

### Recommendation

**Approach A.** It is the only option that keeps G1, G4, pass-by-reference, and YAGNI together. Approach B is rejected because it contradicts the runtime’s hard requirement. Approach C is rejected as premature packaging of provider and persistence concerns.

---

## 4. Decisions (PRD forks, closed)

These replace the PRD’s Open Questions and the two internal contradictions. They are binding for Phase 1.

### 4.1 LLM client interface (Open Question 1)

**Decision: a minimal internal `ModelClient` protocol. No `litellm`.**

`ModelClient` is a `typing.Protocol` with one method:

- `complete(messages: list[ModelMessage]) -> ModelResponse`

`ModelMessage` has `role` in `{system, user, assistant}` and `content: str`. `ModelResponse` has `content: str` (the text the runtime will treat as a Predict JSON payload or a CodeAct cell) and an optional `raw` object the runtime ignores.

Phase 1 ships one adapter, `OpenAICompatibleClient(base_url, api_key, model, timeout_seconds)`, talking to an OpenAI-compatible chat-completions endpoint. The host constructs it and passes it into `AgentRuntime`. A native Anthropic adapter is a later adapter on the same protocol, not a Phase 1 deliverable.

`ModelClient` lives next to `runtime` as an interface `runtime` depends on. `core` does not import it. Tests ship `ScriptedModelClient`, which is a real adapter (not a monkeypatch of the runtime) and maps turn index / last-message matchers to canned `content`. Exhausting the script raises; tests must not silently fall through.

### 4.2 History persistence default (Open Question 2)

**Decision: in-memory only.**

`InMemoryEventLog` is the Phase 1 default and the only shipped adapter. `EventLog` already includes `query` and `collapse` so a later SQLite/file adapter does not change the interface. Resume-across-process is not a Phase 1 behavior. If a host needs durability they will inject a future adapter; Phase 1 does not invent that adapter.

### 4.3 Feature / E2E deterministic LLM (Open Question 3)

**Decision: fully scripted mock, not VCR.**

The Feature/E2E tier asserts control flow, contracts, previews, and termination against `ScriptedModelClient`. That is what “deterministic LLM client” means in Phase 1 CI.

Record/replay of real model HTTP is deferred. **Interface-capability tests** (can a *real* model use typed methods, previews, REPL, recovery) are a distinct track from the four release tiers: small scenarios, 5 runs per supported model, 0/5 vs intermittent reported separately. They are not a Phase 1 merge gate and they do not run in the default CI job.

### 4.4 Sandbox execution model (Open Question 4 + contradiction with §10)

**Decision: in-process execution with interpreter-level restrictions (PRD §6.4 option A). Not subprocess-per-action.**

§10’s “sandbox with subprocess isolation” is overridden. Subprocess-per-action is Approach B and is incompatible with pass-by-reference.

`InProcessExecutor` runs each CodeAct cell in the agent process against the live namespace. Safety in Phase 1:

- Restricted `__builtins__` (no `eval`, `exec`, `compile`, `input`, `__import__`, `open`, `breakpoint`).
- AST pre-check that rejects those names even if the cell tries to reach them via `getattr` on a smuggled builtin the host did not pass in. The reject list is closed: `eval`, `exec`, `compile`, `input`, `__import__`, `open`, `breakpoint`, plus attribute access to `__subclasses__`, `__globals__`, `__code__`, `__builtins__`.
- Default allowlists are empty: `allowed_imports=()`, `allowed_open_paths=()`. The host may pass non-empty allowlists into the executor constructor.
- Per-cell timeout (default 30s) surfaces as `ExecutionTimeout`. The observable is: the cell does not contribute a `return_result`, the observation is the timeout error, the loop may continue until `max_turns`.

`InProcessExecutor` protects the **agent loop** from confused-deputy cells. It does **not** protect the host. A validator bug or an allowed import is a host compromise. Process/container/VM isolation around the whole agent is a deployment requirement, documented as such, and a Phase 3 `Executor` adapter (gVisor/container) — not something Phase 1 re-implements per cell.

### 4.5 How tools are declared (contradiction §5 `@tool` vs §6.1 ellipsis + `@strategy`)

**Decision: the method body declares the kind. There is no `@tool` decorator.**

| Body | Meaning |
|---|---|
| Real Python implementation | Deterministic tool. Callable by the model as an ordinary method. Testable as a function. |
| Ellipsis literal `...` | Agentic. The runtime completes the call via the method’s strategy. |

`@strategy(...)` is how an agentic method chooses *how* the loop runs. It does not change the signature.

- `@strategy()` or `@strategy(CodeActStrategy())` → CodeAct (default).
- `@strategy(PredictStrategy())` → single typed LLM call with local retry.
- `@strategy` on a method with a real body is a **load-time error**.
- A `...` body is enough to mark the method agentic; omitting `@strategy` means `CodeActStrategy()`.
- Names starting with `_` are not published to the model, regardless of body.

§5’s phrase “methods decorated with `@tool`” is replaced by the table in §5 of this spec.

### 4.6 Model Context Protocol (review addition; not a PRD open question)

**Decision: consume MCP servers as composed objects. Do not add a JSON tool-call path. Do not parse MCP config files inside the library. The `mcp` extra is specified here and ships after the Phase 1 loop as `agentframe[mcp]`.**

MCP is how a host attaches GitHub, filesystems, browsers, and other tool servers without writing a method per tool. It is not a second agent runtime.

Three ways to attach MCP were compared:

- **A — Composed `McpClient` field (recommended).** The host constructs a client, `connect()`s it, assigns it to an agent field (`self.github = client`). `tools/list` becomes public methods on that object. A CodeAct cell calls `self.github.create_issue(title=...)`. Resources and prompts are methods on the same object (`read_resource`, `get_prompt`). Matches G1 (object composition) and G4 (code-as-action). Namespacing is free: two servers are two fields.
- **B — Flatten every MCP tool into the REPL as a bare function.** Collides as soon as two servers export `search`. Not an object. Rejected.
- **C — Offer MCP tools through a JSON tool-calling sidecar next to CodeAct.** Reintroduces the protocol G4 exists to avoid. Rejected.

**What Phase 1 must already do** so A does not patch `runtime` later: the static catalog includes public callables on public instance fields (`self.github.create_issue`), not only methods defined on the `Agent` subclass. A plain Python object assigned to a field is enough; `McpClient` is one such object.

**What `agentframe[mcp]` ships:** `McpClient`, `McpTransport` protocol, `StdioTransport`, `StreamableHttpTransport`, `McpError`, `McpResult`, `FakeMcpTransport` (tests). See §8.6.

**Out of the `mcp` extra:** exposing an `Agent` *as* an MCP server; MCP sampling (server-initiated LLM calls); `resources/subscribe`; `roots`; loading `claude_desktop_config.json` / `mcp.json` inside the library (the host may read those files and pass constructor args).

---

## 5. Concept map (Phase 1 contract)

If a module cannot be explained in this table, it does not belong in the framework. Phase 1 implements the first twelve rows; MCP consume is the composed-field row and ships as an extra.

| Concept | Python / OOP primitive |
|---|---|
| Agent | Instance of `Agent` or a subclass |
| State | Instance fields bound in `__init__` |
| Deterministic tools | Public methods with a real body |
| Agentic methods | Public methods whose body is `...`, optionally annotated with `@strategy` |
| Prompt | Class and method docstrings |
| Contracts | Type annotations, validated by `contracts.validate_output` |
| Working memory | Those same instance fields (no MemoryAPI in Phase 1) |
| Workflow | Ordinary Python control flow (`if` / `for` / `while`). The host calls methods. |
| Multi-agent | Object composition (an `Agent` field). No `compose()` helper. |
| Actions | Generated Python cells, executed in-process |
| Execution | `AgentRuntime` think → act → observe |
| History | Append-only `Event` log (`InMemoryEventLog`) |
| MCP server | Composed field: an `McpClient` (or any object) whose public methods are tools |
| MCP tool | Method on that field, invoked from a CodeAct cell as ordinary Python |
| MCP resource / prompt | `read_resource(uri)` / `get_prompt(name, **args)` on the same client |
| Retrieval | Not in Phase 1. Later: a composed `Retriever` object, never an `Agent` base method |

No new DSL. Graphs, YAML node configs, and JSON-tool-call chains are not part of the developer or model interface.

---

## 6. Requirements this spec keeps

These are design requirements, not slogans.

- **G1 — Native mapping.** The table in §5 is the spec. New syntax is forbidden where Python already has an answer.
- **G2 — Interface-only modularity.** A module may import another module’s ABC/Protocol, never its concrete class. Enforced by an `import-linter` contract in CI. No global mutable registries, logs, or stores; everything is instance-owned and passed in. Swapping an executor or client is a constructor argument, never a config file the library parses. Internal ABCs (`Executor`, `EventLog`, `ModelClient`) are a versioned interface: breaking a signature is a major-version bump.
- **G3 — Four-tier test gate.** Nothing merges to the release branch, and no version ships, unless unit, integration, feature/E2E, and contract tiers are green at the thresholds in §11.
- **G4 — Code-as-action.** The model acts by writing Python, not by emitting a JSON tool-call list. Deterministic methods are invoked from that Python as callables.
- **Pass-by-reference.** Arguments and cell results are live locals. Only a bounded preview enters the prompt. The amount of data an agent can process is bounded by the process, not the context window. This is a hard runtime requirement.
- **Validated termination.** An agentic method returns to the caller only after `validate_output` accepts the value against the return annotation. “I’m done” in prose is not termination.
- **Three-region context.** Static prefix (cacheable), append-only event history, dynamic tail. See §9.
- **G5 (RAG)** is a later-phase product goal, not a Phase 1 build requirement. When it exists it is a composed object behind its own extra; `core` never grows an `Agent.retrieve()`.
- **MCP consume** is a product requirement. It is the same shape as G5: a composed object behind `agentframe[mcp]`, never `Agent.call_mcp()` and never a JSON tool-call list. `core` does not import `mcp`. The Phase 1 loop must still be green with the extra uninstalled (the removable-test rule).

---

## 7. Architecture

Phase 1 is a library, not a service. The host process owns the agent objects, the runtime, and the process boundary.

```
host application
    │
    │  constructs Agent, ModelClient, Executor, EventLog
    │  (optional) constructs McpClient(s), connect(), assign to agent fields
    │  calls AgentRuntime.run(...)
    ▼
┌──────────── runtime ─────────────────────────────────────┐
│  bind runtime on the agent                               │
│  classify call → Predict loop or CodeAct loop            │
│  render three-region context                             │
│  ModelClient.complete(...)                               │
│  (CodeAct) Executor.execute(source, namespace)           │
│  contracts.validate_output(...)                          │
│  EventLog.append(...)                                    │
└───────┬───────────────┬───────────────────┬──────────────┘
        │               │                   │
        ▼               ▼                   ▼
   ModelClient     Executor            EventLog
   (protocol)      (protocol)          (protocol)
        │               │                   │
        ▼               ▼                   ▼
 OpenAICompatible  InProcessExecutor  InMemoryEventLog
        │
        ▼
   host's LLM endpoint
```

`core` sits under the agent object: it knows how to describe the class (docstrings, fields, which methods are tools vs agentic) and it does not know how to talk to a model or execute a cell. `contracts` is a pure function module. `runtime` is the only module that orchestrates the others, and it only imports their interfaces plus `core`’s declarations.

**Seams (real, because each already has or will have a second adapter):**

| Seam | Interface | Phase 1 adapter | Later adapter (not built now) |
|---|---|---|---|
| Model | `ModelClient` | `OpenAICompatibleClient`, `ScriptedModelClient` | Anthropic native, others |
| Execution | `Executor` | `InProcessExecutor` | container/gVisor |
| History | `EventLog` | `InMemoryEventLog` | SQLite / file |
| MCP wire | `McpTransport` | (not in Phase 1 install) `StdioTransport`, `StreamableHttpTransport`, `FakeMcpTransport` | — |

One adapter is a hypothetical seam; two is a real one. `ModelClient` already has two Phase 1 adapters (network + scripted), so that seam is real. `Executor` and `EventLog` are versioned interfaces now so Phase 2/3 can add adapters without rewriting `runtime`; Phase 1 still ships only one of each. `McpTransport` becomes a real seam when the extra ships two live adapters plus the fake.

**Dependency direction (import-linter layers):**

- `contracts` → (pydantic only)
- `core` → nothing (stdlib + `inspect`)
- `history` → nothing
- `sandbox` → nothing
- `runtime` → `core` declarations, `contracts` functions, `sandbox.Executor` protocol, `history.EventLog` protocol, `ModelClient` protocol
- `mcp` (extra) → `contracts` functions only; never `core`, `runtime`, or a concrete transport from another module

No arrow goes at a concrete class across those lines. `runtime` must not import `InProcessExecutor` or `InMemoryEventLog`; the host (or a thin `agentframe` façade the *application* imports) wires them. `core` / `runtime` must not import `mcp`. The extra is absent in the modularity CI job.

The public import surface the host is expected to use:

- `Agent`, `strategy`, `PredictStrategy`, `CodeActStrategy`
- `schema_from_signature`, `validate_output`
- `Event`, `EventLog`, `InMemoryEventLog`
- `Executor`, `InProcessExecutor`, `ExecutionTimeout`
- `AgentRuntime`, `ModelClient`, `ModelMessage`, `ModelResponse`, `OpenAICompatibleClient`
- (extra `agentframe[mcp]`) `McpClient`, `McpTransport`, `StdioTransport`, `StreamableHttpTransport`, `McpError`, `McpResult`

A convenience façade may re-export those names. It is application-facing, not a license for `core` to import `runtime` or `mcp`.

---

## 8. Components

Each Phase 1 module has one interface, one implementation story, and no reach into another module’s concrete classes.

### 8.1 `core` — Agent and strategy declarations

**Interface.** `Agent`, `strategy()`, `PredictStrategy`, `CodeActStrategy`. Load-time errors for illegal decorator/body combinations.

**`Agent` field binding.** Annotated attributes on the subclass are the constructor contract. Missing required fields (annotation, no default) raise `TypeError` at init. Unexpected kwargs raise `TypeError`. Class-level defaults are `copy.deepcopy`’d onto the instance so mutable defaults do not leak across instances.

**Method catalog.** On subclass creation (`__init_subclass__`), `Agent` records:

- public deterministic methods (real body, name not starting with `_`)
- public agentic methods (`...` body, optional `@strategy`)

Dunder methods and `Agent`’s own helpers are excluded. The catalog is readable by `runtime` without `runtime` parsing source itself.

**Strategy objects are declarations, not loops.** They carry config only:

- `PredictStrategy(max_retries=3, argument_render_cap_bytes=8192)`
- `CodeActStrategy(max_turns=20, cell_timeout_seconds=30.0)`

The loops live in `runtime`, keyed by strategy type. `core` does not import `runtime`. An agentic method descriptor looks up a runtime bound on the instance as `agent.__runtime__`. If that attribute is missing or `None`, calling the method raises `RuntimeUnboundError` with the method name.

**Reserved instance names.** `Agent` reserves `__runtime__` and `events`. A subclass that annotates either name as a field is a load-time `TypeError`. `core` reserves the strings only; it does not import `EventLog`.

**Composed-field catalog (Phase 1, required for MCP).** At the start of an agentic call the runtime snapshots public callables on public instance fields, excluding reserved names (`__runtime__`, `events`) and primitives (`str`, `bytes`, `int`, `float`, `bool`, `None`, `Enum`). Each appears in the static prefix as `field.method(name: type, ...) -> ret` using `schema_from_signature` when annotations exist, otherwise the MCP/JSON schema the object exposes via an optional `method.__tool_schema__` dict. Names starting with `_` on the field object are omitted. Nested `Agent` values are listed as a field preview only in Phase 1 (no auto-published nested agentic methods until `compose`); the host calls them from Python if needed.

This catalog is why a connected `McpClient` assigned to `self.github` is visible to the model with no `runtime` change.

**Per-method model override is not in Phase 1.** One `ModelClient` on the `AgentRuntime` serves every method. Adding a `model=` field to a strategy later does not change method signatures.

### 8.2 `contracts` — schemas and validation

**Interface.**

- `schema_from_signature(fn) -> dict` — JSON Schema object derived from the callable’s type hints (parameters and return). Used to describe deterministic methods in the static prompt and to describe Predict’s expected JSON.
- `validate_output(value, annotation) -> value` — coerce/validate with Pydantic v2. On failure raise `ValidationError` (Pydantic’s). Never return a half-valid value.

Supported annotations in Phase 1: primitives, `list`/`dict`/`tuple` of those, `Optional`/`Union`, `Literal`, `Enum`, Pydantic `BaseModel`, dataclasses. Other annotations fail closed at catalog time with a clear error, not at the first model turn.

`contracts` does not import `core`.

### 8.3 `history` — queryable append-only log

**`Event` fields:** `tag` (opaque unique string), `type` (see closed set), `payload` (JSON-able dict), `timestamp` (timezone-aware UTC), `agent_id` (string).

**Phase 1 event types (closed set):** `TaskStarted`, `ModelTurn`, `Execution`, `Observation`, `ValidationError`, `Termination`, `Collapse`. New types belong to a later spec.

**`EventLog` interface:**

- `append(event: Event) -> None`
- `query(*, type: str | None = None, limit: int | None = None, include_collapsed: bool = True) -> list[Event]` — chronological. `type` filters exactly. `limit` is the last N matches.
- `collapse(start_tag: str, end_tag: str, summary_text: str) -> Event` — inserts a `Collapse` event. Default history *rendering* replaces the closed range with that summary. `query()` still returns the original events unless `include_collapsed=False`. Unknown tags raise `KeyError`.

**`InMemoryEventLog`** holds a list. It is lost when the process exits. That is the intended Phase 1 default.

No module-level log. The host (or `AgentRuntime`) owns the instance.

### 8.4 `sandbox` — in-process cells

**`Executor` interface:** `execute(source: str, namespace: dict) -> ExecutionResult`.

**`ExecutionResult` fields:** `stdout: str`, `stderr: str`, `display` (value of the last expression if the cell’s last statement is an expression, else `None`), `error` (`Exception` instance or `None`), `timed_out: bool`.

The executor does not know about agents, strategies, or `return_result`. The runtime installs `return_result` (and the tool callables) in `namespace` before `execute`. After `execute` returns, the runtime reads its own side channel to see whether `return_result` was called.

**`InProcessExecutor` behavior:**

- Compile/exec against a copy of `namespace` plus restricted builtins.
- Apply the AST reject list in §4.4 before exec.
- Honour `allowed_imports` / `allowed_open_paths` (default empty).
- Capture stdout/stderr.
- If the last statement is an expression, evaluate it as `display` (notebook-style).
- On timeout: `timed_out=True`, `error=ExecutionTimeout(...)`, do not apply partial `return_result`.
- On exception from the cell: `error` set, `display` unset.
- Mutations to objects already in `namespace` are visible to the caller (same process, pass-by-reference). New names assigned in the cell are written back into `namespace` so the next cell of the same agentic call sees them.

### 8.5 `runtime` — the loop

**Interface.** `AgentRuntime(model, executor, events, *, default_agent_id: str | None = None)` then:

- `run(agent, *args, method: str = "run", **kwargs) -> object`

`run` binds the runtime on `agent` for the duration of the call (`agent.__runtime__ = self` and `agent.events = self.events`), invokes the named agentic method, unbinds `__runtime__` in `finally` (the log reference on `agent.events` remains so the host can inspect it), and returns the validated Python value. It does not wrap the value in an envelope. Traces live on `runtime.events` (the same `EventLog` instance passed in).

If `method` is missing, not agentic, or not public, `run` raises `AttributeError` / `TypeError` before any model call.

**Binding rule.** Nested agentic calls on the *same* agent reuse the bound runtime (stack discipline, one event log). A nested call starts its own CodeAct/Predict loop and its own REPL locals; it does not see the caller’s cell locals. Concurrent calls on one agent from two threads are unsupported in Phase 1; the runtime does not interleave turns.

**`agent_id`.** `f"{type(agent).__name__}-{id(agent):x}"` unless the host passed `default_agent_id` and this is the top-level agent.

**Predict loop.** Render arguments *in full* up to `argument_render_cap_bytes` (over-cap values become a preview plus an error that Predict cannot inspect further — Predict has no REPL). Call `ModelClient.complete`. Parse `content` as JSON, `validate_output` against the return annotation. On `ValidationError`, append `ValidationError`, retry up to `max_retries`. After the last failure, raise that `ValidationError` to the host. No executor is used.

**CodeAct loop.** See §9. Privileged names in the namespace: `self` (the live agent), the method’s arguments, every public deterministic method as a bound callable, every other public agentic method as a bound callable, and `return_result(value)`. There is no nested `execute_python` builtin: the turn *is* the execute step.

The static prompt tells the model to either compute in a Python cell or terminate with `return_result(...)`. JSON tool-call protocol is not offered.

### 8.6 `mcp` extra — consume MCP servers as objects

**Not in the Phase 1 install.** Specified now so the extra is not invented ad hoc. Removable-test: the Phase 1 suite stays green with `agentframe[mcp]` uninstalled.

**Interface.**

- `McpTransport` protocol: `open() -> None`, `close() -> None`, `request(method: str, params: dict) -> object`. One JSON-RPC request/response. The client owns `initialize` / `notifications/initialized` / `tools/list` / `tools/call` / `resources/list` / `resources/read` / `prompts/get`.
- `StdioTransport(command: str, args: tuple[str, ...] = (), env: dict[str, str] | None = None, cwd: str | None = None)` — spawn a local MCP server on stdio. Child lifetime is the transport’s `open`/`close`.
- `StreamableHttpTransport(url: str, headers: dict[str, str] | None = None, timeout_seconds: float = 30.0)` — Streamable HTTP as defined by the MCP spec current at implementation time. SSE-only legacy transport is not shipped.
- `FakeMcpTransport` — in-process adapter that maps method names to callables the test registered. No subprocess, no sockets. This is the E2E/contract double.
- `McpClient(transport: McpTransport)` with:
  - `connect() -> None` — `open`, handshake, `tools/list`, bind methods. Must run before `AgentRuntime.run`.
  - `close() -> None` — close the transport. Context-manager form (`with McpClient(...) as c`) is required.
  - `list_tools() -> list[str]` — Python names after slugify.
  - `read_resource(uri: str) -> McpResult`
  - `list_resources() -> list[str]`
  - `get_prompt(name: str, **arguments) -> str`
  - One public method per MCP tool, name slugified (non-identifier characters become `_`; leading digits get a `t_` prefix; collisions after slugify get `_2`, `_3`, …). Each bound method validates kwargs against the tool’s `inputSchema` (via `contracts`, which must accept a JSON Schema dict as well as a signature — add `validate_output(value, schema: dict)` overload when this extra lands; Phase 1 `validate_output` stays annotation-based).
- `McpResult` — `text: str` (concatenated text parts), `content: list` (raw MCP content parts, live object, previewed), `is_error: bool`.
- `McpError` — raised on JSON-RPC error, handshake failure, unknown tool, or `isError` from `tools/call`. Never returned as a silent `McpResult`.

**How a cell sees it.** After `connect()` and `agent.github = client`, the Phase 1 field catalog publishes `github.create_issue(...)` etc. The cell writes `self.github.create_issue(title="x")`. That is a normal Python call into `McpClient`, which performs `tools/call`. The return is an `McpResult` bound as a live local; only the preview enters the prompt.

**Host wiring (no config file parser):**

```
github = McpClient(StdioTransport("npx", ("-y", "@modelcontextprotocol/server-github"), env={"GITHUB_TOKEN": token}))
github.connect()
agent = SupportAgent(github=github, ...)
```

The host may read Claude/Cursor MCP JSON itself. The library does not.

**Security.** A stdio server is a child process the *host* chose, same trust class as a deterministic method the host wrote. The sandbox still forbids the model from `subprocess` / `socket` / `__import__`. The extra does not widen executor allowlists.

**Sampling, subscribe, server-role.** Not in this extra. An `Agent` is not exported as an MCP server here.

---

## 9. Data flow

A run is a host call into `AgentRuntime.run`, then a per-strategy loop of render → model → (optional) execute → validate.

### 9.1 Host starts a run

1. Host constructs `agent`, `OpenAICompatibleClient` (or `ScriptedModelClient`), `InProcessExecutor`, `InMemoryEventLog`, and `AgentRuntime`. If using MCP, constructs `McpClient`s, `connect()`s them, and assigns them to agent fields *before* this step.
2. Host calls `runtime.run(agent, task)` (or another `method=`).
3. Runtime binds, snapshots the composed-field catalog into the static prefix, appends `TaskStarted`, and enters the strategy loop.

### 9.2 Three-region render (every model turn)

1. **Static prefix** (computed once per agentic call, reused unchanged): a short framework system prompt, the active strategy instructions, the class docstring, the method docstring, the published method signatures on the agent, and the published callables on public instance fields (`field.method(...)`, including a connected `McpClient`). Concatenated into one `system` message so a prefix-caching provider can reuse it. Tools that appear on an MCP server after this snapshot are invisible until the next `run`.
2. **Event history** (append-only): rendered as the following `assistant` / `user` messages. A `ModelTurn` is an `assistant` message (the cell or Predict payload). `Execution` / `Observation` / `ValidationError` are `user` messages. A collapsed range is rendered as the summary only. History grows only by appending; earlier messages are not rewritten.
3. **Dynamic tail** (re-evaluated every turn, last `user` message): bounded previews of `self` fields, current REPL locals (CodeAct), remaining turns, and the current task argument previews on the first turn.

Pass-by-reference preview format (sequences): `name = list(len=100, [:5]=[...], [-5:]=[...])` — concrete type, true length, short head/tail. Scalars: full `repr` if it fits in 512 characters, otherwise type + length + head/tail. Per-value cap 2 KiB; per-observation cap 8 KiB. The live object is not truncated.

Media (images/audio/files as native content blocks) is not in Phase 1. Arguments are text-previewed even if their Python type is richer.

### 9.3 CodeAct turn

1. Render §9.2.
2. `ModelClient.complete` → `content` is treated as Python source (a cell). Append `ModelTurn`.
3. `Executor.execute(content, namespace)`. Append `Execution` (stdout/stderr/error/timeout flags, not the live objects).
4. If the runtime’s `return_result` side channel is set: `validate_output(value, return_annotation)`.
   - Success: append `Termination`, return `value` to the host.
   - Failure: append `ValidationError` with the error text, clear the side channel, continue the loop.
5. Else: append `Observation` with stdout, stderr, and a preview of `display` / new locals. Continue.
6. If `max_turns` is exhausted without a valid `return_result`: raise `TurnLimitExceeded` to the host. Do not return an unvalidated value.

REPL locals persist across cells of this call and are discarded when the call returns. Assignments to `self.*` persist as ordinary Python.

### 9.4 Deterministic method or MCP method from a cell

A cell may call `self.helper(...)` or `self.github.create_issue(...)`. That is a normal Python call. It is not a JSON tool call. The runtime does not intercept it. If `helper` is itself agentic, the descriptor starts a nested loop on the same bound runtime (step 9.3 / Predict as appropriate). The cell then receives the nested call’s validated return (or `McpResult`) as a live object. A `McpError` raised from the client is a cell exception: captured, shown, loop continues.

### 9.5 What never enters the prompt

The full bytes of a large argument and the unused middle of a sequence. Collapsed event *bodies* do not reappear in default history rendering.

`self.events` is the live `EventLog` (set at bind). A CodeAct cell may call `self.events.query(...)` and `self.events.collapse(...)` as ordinary Python — that is how history is queryable by both the developer and the agent, without a separate tool wrapper or a `core` import of `history`. Programmable context-block APIs (named static/dynamic blocks the model edits) are not in Phase 1; rendering uses the defaults in §9.2.

---

## 10. Error handling

Errors are exceptions. There is no parallel result-monad API.

| Situation | What happens |
|---|---|
| Agentic method called with no runtime bound | `RuntimeUnboundError` — no model call |
| `@strategy` on a real body, or un-annotated illegal combo | Load-time `TypeError` at class creation |
| Unsupported type annotation on a published method | Load-time `TypeError` at class creation |
| `run(..., method=)` names a missing / non-agentic method | `AttributeError` / `TypeError` before any model call |
| Predict / CodeAct output fails the return contract | `ValidationError` event; Predict retries; CodeAct continues. After Predict’s last retry, the exception propagates to the host |
| Cell raises (syntax, `NameError`, tool exception) | Captured in `ExecutionResult.error`; observation is the traceback; loop continues |
| Cell uses a rejected builtin / AST pattern | Executor sets `error` describing the reject; loop continues |
| Cell exceeds `cell_timeout_seconds` | `timed_out=True`, `ExecutionTimeout` in `error`; loop continues |
| `max_turns` reached | `TurnLimitExceeded` to the host |
| `ModelClient.complete` raises (network, 4xx/5xx) | Propagates to the host. Runtime does not retry provider errors in Phase 1 |
| `collapse` with unknown tags | `KeyError` |
| `ScriptedModelClient` script exhausted | Raises to the test (fail loud) |
| `McpClient.connect` / handshake fails | `McpError` to the host *before* `run` (host called `connect`) |
| MCP `tools/call` JSON-RPC error or `isError` | `McpError` in the cell; observation is the traceback; loop continues |
| MCP extra imported by `core` / `runtime` | Import-linter failure; merge blocked |

Tracebacks shown to the model include the cell source and caret/line context so the next turn can repair the cell. They are ordinary Python exceptions, so `pdb` on a deterministic helper or on `Executor.execute` works in-process without framework-specific tooling.

Provider errors are not swallowed. Validation errors are never silent success.

---

## 11. Testing

G3 is a hard gate. Phase 1 CI is red unless all four tiers below pass. Interface-capability (live models) is documented here and **not** wired as a merge gate.

| Tier | What it covers in Phase 1 | Threshold |
|---|---|---|
| **Unit** | Catalog/classification, field binding, deepcopy defaults, `schema_from_signature`, `validate_output`, preview formatting, AST reject list, `Event` construction, `InMemoryEventLog.query`/`collapse`, strategy defaults | ≥ 90% line coverage **per module** (`core`, `contracts`, `history`, `runtime`, `sandbox`) |
| **Integration** | Every Phase 1 module-pair that actually collaborates: `runtime`+`sandbox` (cell mutates a live object the next cell sees), `runtime`+`history` (one event per turn, collapse hides range in render), `runtime`+`contracts` (bad `return_result` continues; good one stops), `runtime`+`core` (descriptor bind / `RuntimeUnboundError`) | ≥ 1 test per pair listed |
| **Feature / E2E** | Three fixture agents against `ScriptedModelClient`, each also used as a documented example so docs cannot drift | All three green |
| **Contract** | Shared suite parametrized over shipped adapters: every `Executor` (`InProcessExecutor`), every `EventLog` (`InMemoryEventLog`), every `ModelClient` used in CI (`ScriptedModelClient`; `OpenAICompatibleClient` is contract-tested with a fake HTTP endpoint, not a live vendor) | 100% of shipped adapters pass |

**Three canonical E2E agents (the Feature tier):**

1. **Predict classifier** — one agentic method, `-> Literal[...]` or a small Enum. Scripted client returns invalid JSON, then valid JSON. Assert retry, then the typed value.
2. **CodeAct + live list** — method takes a `list` of ≥ 100 items. Scripted client emits a cell that indexes the tail (`data[-1]`) and `return_result`s it. Assert the returned object is the real last item, and that no event payload contains the middle of the list (preview bounds hold).
3. **Validated termination** — scripted client first `return_result`s the wrong type, then a cell that returns the right type. Assert one `ValidationError` event and a successful host-level return.

**Additional CI jobs (Phase 1):**

- **Modularity.** `import-linter` contracts matching §7. A job that imports and unit-tests `core` and `contracts` without importing `InProcessExecutor` or `OpenAICompatibleClient`. The same job (and the full Phase 1 suite) must pass with `mcp` uninstalled.
- **Sandbox adversarial.** Cells that attempt `eval`, `exec`, `open('/etc/passwd')`, `socket`/`urllib`, an infinite loop, and `__subclasses__` probing. Each is rejected or timed out. This suite is required before `InProcessExecutor` is called stable; it ships in Phase 1.

**When `agentframe[mcp]` ships**, add (not Phase 1 CI): unit tests for slugify/collisions and schema validation; contract suite over `StdioTransport`, `StreamableHttpTransport`, and `FakeMcpTransport` against a tiny in-repo fixture server; one Feature/E2E agent whose field is an `McpClient(FakeMcpTransport)` and whose scripted cell calls `self.server.echo(text="hi")` and `return_result`s the `McpResult.text`. Live third-party servers (`npx` GitHub, etc.) are not a merge gate.

Coverage is measured on the library modules, not on tests or scripts.

---

## 12. Non-functional constraints (Phase 1)

- **Debuggability.** Deterministic methods and `InProcessExecutor.execute` run in the host process. A breakpoint there is a normal breakpoint.
- **Observability.** Every model turn, cell, observation, validation failure, and termination is an `Event` by default. There is no opt-in flag.
- **Security.** Default executor allowlists are empty. The module does not open network connections except inside the host-supplied `ModelClient`. The spec does not claim OS-level isolation.
- **Latency.** `core` and `contracts` perform no I/O. Phase 1’s only network hop is `ModelClient.complete`. MCP I/O happens only inside a host-constructed `McpClient`, during a cell’s Python call.
- **No global mutable state.** Two `AgentRuntime` instances in one process do not share a log, a client, or a registry.

---

## 13. What a later plan must not silently expand

The following are easy to “just add” and are explicitly **not** Phase 1:

- `memory` tools, `BeforeTurn` spontaneous recall, consolidation
- `Retriever` / vector stores / `agentframe[rag]`
- MCP *server* role (export an `Agent` over MCP), sampling, `resources/subscribe`, `roots`, in-library MCP config-file loading
- `compose()`, pub/sub helpers
- `async def` agentic methods, generator pause/resume, token streaming
- Subprocess or container executors
- Persistent `EventLog` adapters
- `@tool` decorator (rejected, not deferred)
- `litellm` (rejected for Phase 1, not deferred as a hidden default)
- Live-model CI as a merge blocker
- Matching NOOA’s SWE-bench / CyberGym numbers
- Distributed execution, GUI, SaaS

---

## 14. Self-review notes

- Placeholders: none. Every PRD open question and both contradictions have a chosen option. MCP consume is a closed decision (composed `McpClient`, extra after the loop).
- Consistency: sandbox is in-process everywhere (architecture, components, data flow, testing, deferred list). Tools are body-convention everywhere; `@tool` appears only as the rejected alternative. MCP is never a JSON tool-call sidecar.
- Scope: Phase 1 is still the five-module loop plus the composed-field catalog. The `mcp` extra is designed in this spec and is not in the Phase 1 install. RAG, compose, pause/resume, container sandbox stay later.
- Ambiguity closed: entry method defaults to `run`; `run` returns the raw validated value; Predict vs CodeAct behavior; preview caps; closed event-type set; closed AST reject list; scripted E2E, not VCR; `self.events` is the bound `EventLog`; `__runtime__` and `events` are reserved names; MCP tools are methods on a field; host calls `connect()` before `run`; stdio + Streamable HTTP + fake transports; no config-file parser.
