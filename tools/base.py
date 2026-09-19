from abc import ABC, abstractmethod
from google.genai import types


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str
    description: str
    parameters_schema: types.Schema

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Executes the tool logic and returns the string output or error message."""
        pass

    def to_genai_declaration(self) -> types.FunctionDeclaration:
        """Converts the tool definition into a Google GenAI FunctionDeclaration."""
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=self.parameters_schema,
        )
