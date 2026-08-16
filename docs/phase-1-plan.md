# Agentic Framework — Phase 1 Implementation Plan

> **Status**: Plan only. No framework code is written from this document until it's reviewed and execution is explicitly requested.
> **Scope**: `contracts`, `history`, `core`, `sandbox`, `runtime` — per PRD §10 Phase 1. RAG, compose, async pause/resume, and a hardened sandbox are out of scope here.
> **References**: `docs/prd.md` §6 (module breakdown), §7 (modularity requirements), §8 (testing gates). Design decisions that close PRD contradictions live in `docs/superpowers/specs/2026-08-16-oop-native-agent-framework-design.md`.

---

## 1. Build Order

Modules are sequenced by the dependency graph in PRD §6, leaves first:

```
contracts ──┐
            ├──> runtime ──> (integration + E2E + interface-capability suites)
history ────┤
            │
core ───────┤
            │
sandbox ────┘
```

`contracts`, `history`, `core`, and `sandbox` have no dependencies on each other (per PRD §7.1, interface-only cross-module imports) and can be built in any order or in parallel. `runtime` depends on all four and is built last — it's the integration point where pass-by-reference, three-region context rendering, and validated termination actually get exercised together.

**Sequencing note**: build `contracts` first even though order is technically free, because `runtime`'s return-type validation and `core`'s typed method signatures both consume it — having it stable early avoids rework in the other three.

1. `contracts`
2. `history`
3. `core`
4. `sandbox`
5. `runtime` (integration)
6. Interface Capability + Feature/E2E suites, full CI gate wiring

---

## 2. Per-Module Plan

### 2.1 `contracts`
**Deliverable**: `schema_from_signature()` (type hints → JSON schema for tool calling), `validate_output()` (Pydantic validation against a declared return type, structured error on failure).
**Unit tests**: schema generation for primitives, `Optional`/`Union`, nested Pydantic models, `Literal` enums; validation pass/fail cases with assertion on the structured error shape (this error shape is what `runtime`'s retry loop consumes later, so pin it now).
**Exit criteria**: 90%+ coverage, zero dependencies beyond `pydantic`, importable standalone.

### 2.2 `history`
**Deliverable**: `Event` model (`type`, `payload`, `timestamp`, `agent_id`), `EventLog` ABC, `InMemoryEventLog` default impl, `.query(type=..., limit=...)`, `.collapse(start_tag, end_tag, summary_text=...)`.
**Unit tests**: append/query/collapse semantics, tag uniqueness, ordering guarantees, collapse preserving searchability of summarized ranges.
**Contract tests**: shared suite asserting any `EventLog` impl honors query/collapse semantics identically (only one impl exists in Phase 1, but the contract test is written now so Phase 2 backends are held to it automatically).
**Exit criteria**: 90%+ coverage, zero dependencies, importable standalone.

### 2.3 `core`
**Deliverable**: `Agent` base class; ellipsis-body detection (a method body of exactly `...` marks it agentic, anything else is deterministic); public/private tool-surface filtering (leading-underscore methods excluded); docstring-to-prompt extraction via `inspect.getdoc()`; `strategy()` decorator plus `PredictStrategy`/`CodeActStrategy` as data-only strategy descriptors (their actual execution logic lives in `runtime` — `core` only records which strategy a method declared).
**Unit tests**: ellipsis-detection against real Python ASTs (not string matching — must handle a method whose body is a docstring followed by `...`, versus a method that merely returns `None`); underscore-exclusion filtering; docstring extraction with and without a class-level docstring; strategy decorator attaching metadata without altering the method's callable signature.
**Exit criteria**: 90%+ coverage, zero dependencies beyond stdlib + `inspect`, importable and testable with zero optional extras installed (this *is* the modularity gate's baseline case).

### 2.4 `sandbox`
**Deliverable**: `Executor` ABC, `InProcessExecutor` — executes a code string against an injected locals dict (live objects, not serialized copies), enforces a timeout, rejects `eval`/`exec`/`compile`/`input`/blocking event-loop calls with typed errors, captures stdout/stderr/return value/raised exceptions in IPython-traceback format.
**Unit tests**: normal execution returns captured value; timeout enforcement actually interrupts a hanging loop; each denylisted builtin raises the expected typed error rather than executing.
**Security/adversarial tests (PRD §8 gate)**: attempted filesystem escape, attempted network access, fork-bomb-style resource exhaustion, infinite loop under the timeout — each must be caught before this module is marked stable. This gate blocks `sandbox` from being marked done even if unit tests are green.
**Exit criteria**: 90%+ coverage, security gate passed, zero dependencies from other framework modules.

### 2.5 `runtime`
**Deliverable**: `AgentRuntime.run(agent, task) -> Result` — the think→act→observe loop; three-region context assembly (static prefix, event history from `history`, dynamic tail blocks); pass-by-reference argument binding with bounded-preview rendering (type, length, head/tail sample) for anything passed to `sandbox`; strategy dispatch (`PredictStrategy` = single call + local retry via `contracts.validate_output()`; `CodeActStrategy` = loop calling `sandbox.execute()` until `return_result(...)` validates); validated termination (no result returned to the caller until it passes its declared type contract).
**Unit tests**: context assembly ordering (static/history/dynamic) in isolation with mocked sub-parts; preview rendering for large lists/strings/dicts matches the bounded-preview spec exactly (this is worth pinning precisely — it's the mechanism the whole "process data bigger than the context window" claim rests on).
**Integration tests**: `runtime` + `sandbox` executing a real generated action against a real (small) live object, confirming the object is the *actual* object, not a copy (identity check, not just equality); `runtime` + `contracts` rejecting an invalid return and continuing the loop; `runtime` + `history` confirming every tool call and Python execution produces an `Event`.
**Exit criteria**: 90%+ coverage on unit tests, every module-pair boundary listed above covered by at least one integration test (per PRD §8's integration-tier requirement).

---

## 3. Test Suites Stood Up After `runtime` Lands

### 3.1 Interface Capability suite
Adapted from the methodology in the PRD's NOOA precedent: small, focused scenarios (1–5 turns), one interface behavior isolated per scenario. Phase 1 scenario families, scaled down from NOOA's 36 to what Phase 1 actually has surface area for:
- Typed method calls (Predict and CodeAct paths)
- Structured/validated returns, including recovery after a failed validation
- Stateful object manipulation via `self` fields
- REPL/code execution basics (multi-cell state persistence within one call)
- Bounded-preview comprehension (does the model correctly index/slice a previewed large object rather than assuming it only sees the preview)
- Error recovery (a raised exception in `sandbox` is legible enough for the model to fix its own code)

Run each scenario 5× against every model the framework claims to support. Track total-failure scenarios (0/5) separately from intermittent ones, per PRD §8.

### 3.2 Feature/E2E suite
One test per documented README/example — scripted mock `ModelClient` returns pre-defined tool calls/code actions/final answers, so runs are deterministic and fast. This suite verifies the harness does what the docs claim; it does not claim to validate real-model behavior (that's §3.1's job).

### 3.3 CI wiring
- Modularity gate: `core` installs and its test suite passes with `contracts`/`history`/`sandbox`/`runtime` absent from the environment (only stdlib + `inspect`).
- Import-linter contract: no module imports a concrete class from another module, only ABCs/protocols.
- All four tiers (unit, integration, feature/E2E, contract) plus the interface-capability suite gate merges to `main`, per PRD §8.

---

## 4. Milestones

| Milestone | Contents | Gate to pass |
|---|---|---|
| M1 | `contracts`, `history` complete | Unit + contract tests green, both importable standalone |
| M2 | `core` complete | Unit tests green, modularity-gate baseline case passes (zero optional extras) |
| M3 | `sandbox` complete | Unit tests + security/adversarial gate green |
| M4 | `runtime` complete | Unit + integration tests green across every module-pair boundary in §2.5 |
| M5 | Interface Capability + E2E suites stood up, full CI pipeline wired | All gates in PRD §8 running on every PR |
| M6 | Phase 1 done | PRD §8 Definition of Done checklist satisfied for all five modules; README examples exist and are passing E2E tests |

---

## 5. Explicitly Deferred (not in this plan)

RAG, multi-agent composition, async/generator pause-resume, container-hardened sandbox, mutation testing — all per PRD §10, Phase 2/3.
