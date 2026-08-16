# Contributing

## Setup

```bash
git clone https://github.com/nvmaditya/agentframe.git
cd agentframe
uv sync --extra dev
uv run pytest
```

Python 3.11+ and [uv](https://docs.astral.sh/uv/) are enough.

## What to change

Read `AGENTS.md` before writing code. The design spec in `docs/superpowers/specs/` is the contract for Phase 1. Do not start Phase 2 (`mcp`, `rag`, `compose`) in a Phase 1 PR.

## Tests

Every behavior lands with a test that failed first.

```bash
uv run pytest tests/contracts -q
uv run pytest --cov --cov-fail-under=90
uv run lint-imports
```

Feature/E2E tests use `ScriptedModelClient`. Do not call a live model in the default suite.

## Pull requests

- One module or one concern.
- Update the docs that would otherwise be wrong (`README.md`, `AGENTS.md`, spec/plan as needed) in the same commit or PR.
- Keep the import-linter contracts green.
- Conventional commit titles: `feat(core): …`, `fix(sandbox): …`, `docs: …`, `test: …`.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
