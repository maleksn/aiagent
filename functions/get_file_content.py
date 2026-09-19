from tools.file_tools import GetFileContentTool

_tool = GetFileContentTool()
schema_get_file_content = _tool.to_genai_declaration()


def get_file_content(working_directory: str, file_path: str) -> str:
    return _tool.execute(working_directory=working_directory, file_path=file_path)

