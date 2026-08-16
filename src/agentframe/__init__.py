"""agentframe — OOP-native Python agents."""

from agentframe.contracts import schema_from_signature, validate_output
from agentframe.history import Event, EventLog, InMemoryEventLog

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "schema_from_signature",
    "validate_output",
    "Event",
    "EventLog",
    "InMemoryEventLog",
]

