from typing import Any, Callable, Type
from google.genai import types
from tools.base import BaseTool


class ToolRegistry:
    """Registry for managing and dispatching agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool_or_class: BaseTool | Type[BaseTool]) -> Any:
        """
        Registers an instance of BaseTool or a BaseTool subclass.
        Can be used as a function or as a class decorator.
        """
        if isinstance(tool_or_class, type) and issubclass(tool_or_class, BaseTool):
            instance = tool_or_class()
            if not instance.name:
                raise ValueError("Tool must have a non-empty name.")
            self._tools[instance.name] = instance
            return tool_or_class
        elif isinstance(tool_or_class, BaseTool):
            if not tool_or_class.name:
                raise ValueError("Tool must have a non-empty name.")
            self._tools[tool_or_class.name] = tool_or_class
            return tool_or_class
        else:
            raise TypeError("Expected BaseTool instance or subclass.")

    def get(self, name: str) -> BaseTool | None:
        """Retrieves a registered tool by name."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Checks if a tool with given name is registered."""
        return name in self._tools

    def list_tools(self) -> list[BaseTool]:
        """Returns all registered tool instances."""
        return list(self._tools.values())

    def to_genai_tool(self) -> types.Tool:
        """Generates a Google GenAI types.Tool containing all registered tool declarations."""
        return types.Tool(
            function_declarations=[tool.to_genai_declaration() for tool in self._tools.values()]
        )

    def execute(self, name: str, **kwargs) -> str:
        """
        Executes a registered tool by name.
        Returns error string if tool is not found or if execution fails.
        """
        tool = self.get(name)
        if not tool:
            return f"Error: Unknown tool '{name}'"
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return f"Error executing tool '{name}': {e}"


# Global default registry instance
default_registry = ToolRegistry()
