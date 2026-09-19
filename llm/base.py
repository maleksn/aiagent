from abc import ABC, abstractmethod
from typing import Any
from google.genai import types


class BaseLLMClient(ABC):
    """Abstract interface for LLM providers (Dependency Inversion Principle)."""

    @abstractmethod
    def generate_content(
        self,
        contents: list[types.Content],
        tools: list[types.Tool] | None = None,
        system_instruction: str = "",
        temperature: float = 0.0,
    ) -> Any:
        """Sends a request to the LLM and returns the provider response."""
        pass
