# 01 — Refuse an executor that cannot keep the live object

**What to build:** Constructing the runtime with an executor that cannot keep the live object fails immediately. The model is not called and no event is recorded. An in-process executor still runs an agentic method: a list of ten thousand items returns the real tail object, and the middle item appears in no recorded event. A direct cell on the process-isolated executor still runs outside the runtime. The phase notes no longer describe that executor as a loop peer.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] Constructing the runtime with the process-isolated executor raises `TypeError` before any model call and before any event is appended.
- [x] The error states that the runtime requires an executor that keeps the live object, its methods, and `return_result`.
- [x] The runtime decides this from the executor interface (default: does not keep live objects). It does not import a concrete executor.
- [x] The in-process executor opts in. Existing `run` behavior on it stays green.
- [x] A scripted cell that returns the tail of a ten-thousand-item list returns that same object, and no event payload contains a sentinel placed in the middle.
- [x] Calling the process-isolated executor directly, outside the runtime, still executes a cell.
- [x] Status docs that call the isolated executor an optional loop executor are updated in the same change.

## Comments

Implemented on the current branch. The refusal test was red before the constructor check. The large-list test locks the live tail and the unseen middle; it does not itself exercise the refusal. Tickets 02–04 stay open.
