# Security

`InProcessExecutor` restricts the **agent loop** (dangerous builtins, AST reject list, cell timeout). It does **not** isolate the host. A validator bug or an allowed import is a host compromise. Run untrusted tasks inside a process/container/VM you control.

## Report a vulnerability

Open a [GitHub security advisory](https://github.com/nvmaditya/agentframe/security/advisories/new) on this repository. Do not file a public issue for sandbox escapes or secret leaks.

## Scope

In scope: interpreter-level restrictions in `sandbox`, validation of `return_result`, anything that lets generated cells reach `eval` / `exec` / filesystem / network without an explicit host allowlist.

Out of scope: using a host-constructed MCP server or tool that the host chose to trust.
