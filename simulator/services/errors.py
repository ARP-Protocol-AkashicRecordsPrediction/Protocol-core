class SimulatorError(Exception):
    """Base exception for simulator domain failures."""


class LLMConfigurationError(SimulatorError):
    """Raised when an LLM provider is not configured correctly."""


class LLMProviderError(SimulatorError):
    """Raised when an LLM provider call fails."""


class LLMJSONParseError(SimulatorError):
    """Raised when an LLM response cannot be parsed as required JSON."""


class PredictionStateError(SimulatorError):
    """Raised when a prediction run is in an invalid state for an action."""


class MemoryRetrievalError(SimulatorError):
    """Raised when topic memory cannot be retrieved or linked."""

