# AGENTS.md

Instructions for humans and coding agents working in this repository.

## What this is

`agentframe` is a small Python library. An agent is a Python object:

| Concept | Primitive |
|---|---|
| Agent | `Agent` subclass |
| State | instance fields |
| Deterministic tools | public methods with a real body |
| Agentic methods | public methods whose body is `...` |
| Prompt | class and method docstrings |
| Contracts | type annotations + `contracts.validate_output` |
| Actions | generated Python cells, in-process |
| Workflow | ordinary `if` / `for` / `while` |
| History | append-only `EventLog` |
| MCP server | composed field (`McpClient`), not a second protocol |

There is no graph DSL, no YAML node config, and no JSON tool-call loop. If a change needs one of those, it does not belong here.

## Documents (source of truth)

Read in this order when the question is “what should this do?”:

1. `docs/superpowers/specs/2026-08-16-oop-native-agent-framework-design.md` — Phase 1 design (decisions, interfaces, data flow).
2. `docs/prd.md` — product requirements.
3. `docs/phase-1-plan.md` — build order and exit criteria.

If those three disagree, the **design spec wins** (it closed the PRD’s contradictions). Then update the other doc in the same commit.

## Phases

| Phase | Status | Modules |
|---|---|---|
| 1 | implemented | `contracts`, `history`, `core`, `sandbox`, `runtime` |
| 2 | mcp extra implemented; rag/compose not built | composed `McpClient`; `rag` and `compose` still specified only |
| 3 | named only | async pause/resume, container/gVisor executor, mutation testing |

Do not start `rag` / `compose` in a Phase 1 or mcp PR.

## Module rules

- A module may import another module’s ABC/Protocol, never its concrete class.
- `core` depends on nothing (stdlib + `inspect`).
- `contracts` depends on `pydantic` only.
- `history` and `sandbox` depend on nothing else in the package.
- `runtime` orchestrates via interfaces. It must not import `InProcessExecutor`, `InMemoryEventLog`, or `OpenAICompatibleClient`. The application façade (`agentframe/__init__.py`) wires those.
- No module-level singletons. No config-file parsers. Swap backends by passing objects.
- Public names starting with `_` are not model-facing.

Enforced by `import-linter` (`lint-imports`) in CI.

## How to work

```text
uv sync --extra dev
uv run pytest
uv run pytest --cov --cov-fail-under=90
uv run lint-imports
```

- Tests first (red → green → refactor). A test that passes before the code exists is not a test.
- Drive the real public entry point. Do not re-implement the unit under test inside the test.
- Feature/E2E uses `ScriptedModelClient`. Do not add live-model calls to the default suite.
- Interface-capability against a real model is opt-in (`AGENTFRAME_CAPABILITY=1`). CI runs the same scenarios against the scripted client.

## Commit style

One concern per commit. The commit that lands a module also updates the docs that describe it (`README.md`, this file’s phase table, and any spec/plan line that would otherwise lie).

```
feat(contracts): add schema_from_signature and validate_output
feat(history): in-memory EventLog with query and collapse
docs: document composed-field catalog for MCP
```

No generated lockfile churn in feature commits. No drive-by refactors.

## Do not

- Add an `@tool` decorator.
- Execute model code in a subprocess-per-action (breaks pass-by-reference).
- Import `rag` or `mcp` from `core`.
- Parse `mcp.json` / Claude desktop config inside the library.
- Swallow `ValidationError` or provider errors.
- Expand Phase 1 to streaming, async agentic methods, or a persistent event log.
