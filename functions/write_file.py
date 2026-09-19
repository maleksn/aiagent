from tools.file_tools import WriteFileTool

_tool = WriteFileTool()
schema_write_file = _tool.to_genai_declaration()


def write_file(working_directory: str, file_path: str, content: str) -> str:
    return _tool.execute(
        working_directory=working_directory, file_path=file_path, content=content
    )

