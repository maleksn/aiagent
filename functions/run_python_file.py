from tools.execution_tools import RunPythonFileTool

_tool = RunPythonFileTool()
schema_run_python_file = _tool.to_genai_declaration()


def run_python_file(
    working_directory: str, file_path: str, args: list[str] | None = None
) -> str:
    return _tool.execute(
        working_directory=working_directory, file_path=file_path, args=args
    )


