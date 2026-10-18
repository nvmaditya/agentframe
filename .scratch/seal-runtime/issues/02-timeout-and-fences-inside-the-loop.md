# 02 — Cell timeout and fence stripping live inside the runtime

**What to build:** The loop itself strips one markdown fence, does not treat prose as a successful return, and honors the strategy cell timeout. A fenced cell returns the typed value. A cell that sleeps past the timeout is an observation, and the next scripted cell still returns. The example client’s rewriter is not on this path. The day-14 kill is recorded on this ticket: five held-out tasks on a local model must pass with no host rewriter, or later tickets stop.

**Blocked by:** 01 — Refuse an executor that cannot keep the live object

**Status:** ready-for-agent

- [ ] A scripted cell wrapped in one markdown fence returns the annotated value through `run`.
- [ ] Prose that is not a cell does not become a successful return. The method can still succeed on a later cell.
- [ ] A cell that sleeps past the strategy’s cell timeout is recorded as an observation, and the next scripted cell still returns the annotated value.
- [ ] The loop applies that timeout. The example client’s fence cleaner is not required.
- [ ] The day-14 kill is specified and left opt-in (not in the default suite): mutate a field, reduce ten thousand rows without those rows entering the log, a bad type then a good type, one real method call, and a turn limit that raises. If those tasks need the example cleaner, tickets 03 and 04 stop.
