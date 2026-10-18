# 04 — One caller-level decision on a ledger-shaped object

**What to build:** One test a caller could have written. A ledger-shaped object, a scripted client, and `run` either returns a validated decision or raises the turn-limit error. The event log for that run is queryable. No new module.

**Blocked by:** 03 — The model sees only methods the author wrote

**Status:** ready-for-agent

- [ ] `run` on the ledger-shaped object returns a validated decision when the scripted cell returns one.
- [ ] `run` raises the turn-limit error when the scripted cells never return a decision.
- [ ] The event log for the successful run can be queried for the termination.
- [ ] The change adds no new module and no new product type.
