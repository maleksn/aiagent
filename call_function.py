# call_function.py
from collections.abc import Callable
from typing import Any
from config import DEFAULT_WORKING_DIRECTORY
from tools.registry import default_registry
import tools  # Ensure all tools are registered

available_functions = default_registry.to_tools()
function_map: dict[str, Callable[..., str]] = {
    tool.name: tool.execute for tool in default_registry.list_tools()
}


def call_function(
    function_call: Any,
    verbose: bool = False,
    working_directory: str = DEFAULT_WORKING_DIRECTORY,
) -> dict[str, Any]:
    if hasattr(function_call, "name"):
        function_name = function_call.name or ""
        raw_args = getattr(function_call, "args", {}) or {}
    elif isinstance(function_call, dict):
        function_name = function_call.get("name", "")
        raw_args = function_call.get("args", {})
    else:
        function_name = str(function_call)
        raw_args = {}

    if verbose:
        print(f"Calling function: {function_name}({raw_args})")
    else:
        print(f" - Calling function: {function_name}")

    if not default_registry.has(function_name):
        return {
            "role": "tool",
            "name": function_name,
            "content": f"Error: Unknown function '{function_name}'",
        }

    args = dict(raw_args) if isinstance(raw_args, dict) else {}
    args["working_directory"] = working_directory

    function_result = default_registry.execute(function_name, **args)

    return {
        "role": "tool",
        "name": function_name,
        "content": function_result,
    }
