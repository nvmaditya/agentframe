# Seal the runtime

## Problem Statement

A caller who hands an agent a live object — a batch, a ledger, a list too large to paste into a prompt — needs the agentic method to finish against that same object. Today the runtime accepts any executor. The process-isolated executor drops the live object, its methods, and `return_result` before the cell runs, so a typed return becomes a name error. The cell timeout declared on the strategy is never applied. Fence stripping and prose cleanup live in an example client, outside the loop. The prompt lists every public callable on a composed field, including connection and lifecycle methods the author did not write, and it can substitute the base agent docstring when the subclass has none.

The caller cannot trust that `run` either returns the declared type from the live object or fails before any model call.

## Solution

An agentic method is one call. `run` returns the declared type, or the runtime fails at construction when the executor cannot keep the live object, its methods, and `return_result`. Process isolation stays a direct cell runner. It is not a second loop backend. Isolation of a whole agent, if it is ever needed, wraps the agent. It does not replace the loop executor.

Behind that call, in later slices of this same spec: the loop strips one markdown fence, does not treat prose as a successful return, and honors the cell timeout; the prompt names only methods the author wrote; one caller-level test drives a ledger-shaped object through `run` and the event log. No new module.

## User Stories

1. As a caller of an agentic method, I want `run` to return the declared type, so that I can use the result as an ordinary Python value.
2. As a caller, I want the runtime to reject an executor that cannot keep the live object, so that a cell is never started on a copy that has lost the object.
3. As a caller, I want that rejection at construction, so that I find out before a model call and before any event is recorded.
4. As a caller, I want the rejection to name the requirement (the live object, its methods, and `return_result`), so that I know why this executor cannot drive the loop.
5. As a caller, I want an in-process executor to keep being accepted, so that existing agents keep running against live fields and methods.
6. As a caller passing a list of ten thousand items, I want `run` to return the real tail object, so that the result is the object I passed, not a serialized stand-in.
7. As a caller passing that list, I want no recorded event to contain the middle item, so that a value the model was not shown cannot leak into the log.
8. As a caller, I want a scripted cell that indexes the tail to succeed without the model seeing the middle, so that the model cannot approve a result it computed from the hidden rows.
9. As a caller, I want a future executor to be refused until it declares that it keeps live objects, so that a new adapter cannot silently become a loop backend.
10. As a caller who already runs a single cell in a child process, I want that direct execution to keep working, so that host isolation of one cell remains available outside the loop.
11. As a caller, I want the model not to be invoked when construction refuses the executor, so that a bad wiring spends no tokens and writes no turns.
12. As an agent author, I want the cell timeout on the strategy to be honored by the loop, so that a slow cell becomes an observation instead of running to the executor’s own longer deadline.
13. As an agent author, I want a cell that sleeps past the timeout to leave the loop able to accept the next cell, so that one slow turn does not end the method.
14. As an agent author, I want the loop to strip one markdown fence around a cell, so that a fenced answer still returns the typed value.
15. As an agent author, I want prose that is not a cell to fail as an observation, so that a sentence is not rewritten into a successful return.
16. As an agent author, I want that fence handling and the timeout to live in the runtime, so that an example client is not required to clean model text before `run`.
17. As an agent author, I want a bad return type to be rejected and a later good return to be accepted, so that one validation failure is not the end of the method.
18. As an agent author, I want a turn limit to raise when the model never returns, so that a method cannot spin without a result.
19. As an agent author, I want the system prompt to name the methods I wrote, so that the model calls those methods and not the framework’s.
20. As an agent author, I want the prompt to omit connect, close, list, get-prompt, and read-resource on a composed field, so that lifecycle operations are not offered as tools.
21. As an agent author with no class docstring, I want the prompt to omit the base agent docstring, so that the model is not instructed by a class I did not write.
22. As an agent author, I want those prompt rules to be visible in the messages a scripted model client received, so that the check does not depend on a live model.
23. As a caller of a ledger-shaped object, I want one `run` to return a validated decision, so that a refund-style write is a typed result and not a free-form payload.
24. As a caller of that object, I want `run` to raise the turn-limit error when the model never decides, so that a missing decision is a failure I can catch.
25. As a caller of that object, I want the event log to answer what happened, so that I can query the run without a new module.
26. As a caller, I want that ledger-shaped check to use the objects the library already has, so that the month does not add a product module ahead of the sealed loop.
27. As a maintainer, I want the phase notes to say the loop refuses an executor that does not keep live objects, so that the docs do not still offer process isolation as a loop peer.
28. As a maintainer, I want the in-process executor to remain the loop executor, so that pass-by-reference stays the path `run` actually takes.
29. As a maintainer, I want the runtime to decide this from the executor interface, so that the runtime module does not import a concrete executor.
30. As a maintainer, I want the day-14 check — five held-out tasks on a local model, with no host rewriter — to be allowed to kill the later slices, so that fence and timeout work is judged on the loop itself.

## Implementation Decisions

- The deep module is the runtime. The interface is “finish this method”: `run` returns the declared type, or construction fails.
- The executor interface gains a boolean capability, default false: whether this executor keeps the live object, its methods, and `return_result` in the cell. The in-process executor sets it true. The process-isolated executor leaves it false.
- The runtime reads that capability with a default of false. It does not import concrete executors and does not branch on their classes. Construction raises `TypeError` when the capability is false, before a model call and before appending an event. The message states that the runtime requires an executor that keeps the live object, its methods, and `return_result`.
- Direct execution on the process-isolated executor stays supported. Wrapping a whole agent in a process is out of this spec. The isolated executor does not become a loop peer.
- Cell timeout, single-fence stripping, and “prose is not a successful return” are the second slice. They belong in the loop. The strategy’s cell timeout becomes the deadline the loop enforces. A timed-out cell is an observation. The next cell may still return. The example client’s rewriter is not the implementation.
- The day-14 kill sits on that second slice: five held-out tasks on a local model (mutate a field, reduce ten thousand rows without those rows entering the log, a bad type then a good type, one real method call, and a turn limit that raises). They must pass with no host rewriter. If they need the example cleaner, later slices stop. This kill is opt-in. It is not part of the default suite.
- The third slice narrows what the model is told. The prompt names methods the author wrote on the agent and on composed fields. It does not name connect, close, list-tools, get-prompt, or read-resource. A missing subclass docstring does not fall through to the base agent docstring.
- The fourth slice is one caller-level test on a ledger-shaped object that already fits an agent: scripted model, `run` returns a validated decision or raises the turn-limit error, and the log is queryable. No new module. No commit-door product type.
- Docs that still call the isolated executor an optional loop executor are corrected in the same change as the construction refusal: the phase status, the short status lines, and the design note that says it shipped as an optional loop executor. Historical design text stays, with that one claim brought up to date. Mutation testing stays deferred.
- No new package module. The sandbox stays a leaf the runtime may refuse.

## Testing Decisions

- One seam: `AgentRuntime` construction and `AgentRuntime.run`. Tests call that public entry. They do not call `Executor.execute` to prove the loop seal, and they do not assert private helpers.
- A good test states caller-visible behavior: construction raises, the model client’s call count stays zero, `run` returns the same tail object the caller passed, and the middle of a large list is absent from recorded event payloads.
- Prior art is the existing runtime suite: a live list indexed from a scripted cell, and a failure that happens before the model is called.
- The first slice’s red test is the construction refusal. The large-list identity check locks behavior the in-process loop already has; it is asserted through `run`, with a sentinel the caller chose, not a value recomputed by the test.
- Later slices test at the same seam: a fenced cell and a timeout observation through `run`; prompt contents through the messages the scripted client saw; the ledger-shaped decision through `run` and a log query.
- Default tests stay on the scripted model client. The day-14 local-model kill is opt-in and is not added to the default suite.
- The import-linter contracts stay in force. The runtime still does not import concrete executors.

## Out of Scope

- A ledger, commit-door, or payments module. Week 4 is one test on an object the caller could already have written.
- Making the process-isolated executor able to see `return_result` or `self`. It is refused by the loop instead.
- Wrapping the whole agent in a process, gVisor as a loop backend, and any change that executes each cell in a subprocess.
- MCP surface, RAG backends, blackboard, `compose` changes, a persistent event log, streaming, async agentic methods, provider matrices, memory consolidation, mutation scores.
- Widening the method catalog. The third slice only removes names the author did not write.
- Durable history, embeddings, and one-shot JSON as a product. One-shot JSON stays out; other libraries already own it.
- Rewriting the example model client. The loop must not depend on it.
- Fixing prompt-only names such as remaining turns, except where a slice above explicitly changes the prompt.

## Further Notes

- Source of the sequence: the staff systems designer’s current-state review (NO WEDGE), saved in the reviews doc. The four weeks are four tickets. This spec does not adopt a separate ledger product sketched in a later interface pass.
- The day-14 kill is a stop rule for tickets after the timeout slice. It is not a reason to skip the construction refusal.
- Ticket order is linear: refuse the bad executor, then timeout and fences, then the prompt catalog, then the single caller-level ledger-shaped test.
