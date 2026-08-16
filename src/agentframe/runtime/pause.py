from dataclasses import dataclass


@dataclass(frozen=True)
class Paused:
    """Yielded by AgentRuntime.iterate after a turn that did not terminate."""
