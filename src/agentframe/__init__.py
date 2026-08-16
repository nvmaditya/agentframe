"""agentframe — OOP-native Python agents."""

from agentframe.contracts import schema_from_signature, validate_output
from agentframe.core import (
    Agent,
    CodeActStrategy,
    PredictStrategy,
    RuntimeUnboundError,
    strategy,
)
from agentframe.history import Event, EventLog, InMemoryEventLog
from agentframe.runtime import (
    AgentRuntime,
    ModelClient,
    ModelMessage,
    ModelResponse,
    Paused,
    ScriptExhausted,
    ScriptedModelClient,
    TurnLimitExceeded,
)
from agentframe.runtime.openai import OpenAICompatibleClient
from agentframe.sandbox import (
    ExecutionResult,
    ExecutionTimeout,
    Executor,
    InProcessExecutor,
    IsolatedExecutor,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "schema_from_signature",
    "validate_output",
    "Event",
    "EventLog",
    "InMemoryEventLog",
    "Agent",
    "CodeActStrategy",
    "PredictStrategy",
    "RuntimeUnboundError",
    "strategy",
    "ExecutionResult",
    "ExecutionTimeout",
    "Executor",
    "InProcessExecutor",
    "IsolatedExecutor",
    "AgentRuntime",
    "Paused",
    "ModelClient",
    "ModelMessage",
    "ModelResponse",
    "OpenAICompatibleClient",
    "ScriptExhausted",
    "ScriptedModelClient",
    "TurnLimitExceeded",
]

