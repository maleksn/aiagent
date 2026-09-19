# call_function.py
from collections.abc import Callable
from google.genai import types
from config import DEFAULT_WORKING_DIRECTORY
from tools.registry import default_registry
import tools  # Ensure all tools are registered

available_functions = default_registry.to_genai_tool()
function_map: dict[str, Callable[..., str]] = {
    tool.name: tool.execute for tool in default_registry.list_tools()
}


def call_function(
    function_call: types.FunctionCall,
    verbose: bool = False,
    working_directory: str = DEFAULT_WORKING_DIRECTORY,
) -> types.Content:
    function_name = function_call.name or ""

    if verbose:
        print(f"Calling function: {function_call.name}({function_call.args})")
    else:
        print(f" - Calling function: {function_name}")

    if not default_registry.has(function_name):
        return types.Content(
            role="tool",
            parts=[
                types.Part.from_function_response(
                    name=function_name,
                    response={"error": f"Unknown function: {function_name}"},
                )
            ],
        )

    args = dict(function_call.args) if function_call.args else {}
    args["working_directory"] = working_directory

    function_result = default_registry.execute(function_name, **args)

    return types.Content(
        role="tool",
        parts=[
            types.Part.from_function_response(
                name=function_name,
                response={"result": function_result},
            )
        ],
    )
