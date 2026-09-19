from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str
    description: str
    parameters_schema: dict[str, Any]

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Executes the tool logic and returns the string output or error message."""
        pass

    def to_tool_declaration(self) -> dict[str, Any]:
        """Converts the tool definition into standard OpenAI/OpenRouter function tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

