from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """Encapsulates a function/tool call requested by the model."""
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class LLMResponse:
    """Standardized, provider-agnostic LLM response."""
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: Any = None

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseLLMClient(ABC):
    """Abstract interface for LLM providers (Dependency Inversion Principle)."""

    @abstractmethod
    def generate_content(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_instruction: str = "",
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Sends a request to the LLM and returns the standardized response."""
        pass
