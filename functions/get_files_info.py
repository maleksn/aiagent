from tools.file_tools import GetFilesInfoTool

_tool = GetFilesInfoTool()
schema_get_files_info = _tool.to_genai_declaration()


def get_files_info(working_directory: str, directory: str = ".") -> str:
    return _tool.execute(working_directory=working_directory, directory=directory)

