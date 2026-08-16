"""Type hints → JSON Schema, and Pydantic validation of return values."""

from agentframe.contracts.schema import schema_from_signature
from agentframe.contracts.validate import validate_output

__all__ = ["schema_from_signature", "validate_output"]
