# 03 — The model sees only methods the author wrote

**What to build:** The system prompt names methods the author wrote on the agent and on composed fields. It does not name connect, close, list-tools, get-prompt, or read-resource. When the subclass has no class docstring, the prompt does not substitute the base agent docstring. The check reads the messages the scripted client saw.

**Blocked by:** 02 — Cell timeout and fence stripping live inside the runtime

**Status:** ready-for-agent

- [ ] A scripted run’s system prompt includes a method the author wrote and a method on a composed field that the author exposed.
- [ ] That prompt does not name connect, close, list-tools, get-prompt, or read-resource.
- [ ] An agent subclass with no class docstring does not pick up the base agent class docstring in the messages the scripted client saw.
- [ ] `run` still returns the annotated value for that scripted cell.
