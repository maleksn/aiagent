import os
from typing import Any
from config import config
from tools.base import BaseTool
from tools.registry import default_registry
from tools.security import SecurityError, resolve_safe_path


@default_registry.register
class GetFilesInfoTool(BaseTool):
    name = "get_files_info"
    description = (
        "Lists files in a specified directory relative to the working directory, "
        "providing file size and directory status"
    )
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Directory path to list files from, relative to the working directory (default is the working directory itself)",
            },
        },
    }

    def execute(self, working_directory: str = config.default_working_directory, directory: str = ".") -> str:
        try:
            target_dir = resolve_safe_path(working_directory, directory)
            if not os.path.isdir(target_dir):
                return f'Error: "{directory}" is not a directory'

            items = sorted(os.listdir(target_dir))
            lines = []
            for item in items:
                item_path = os.path.join(target_dir, item)
                is_dir = os.path.isdir(item_path)
                try:
                    size = os.path.getsize(item_path)
                except OSError:
                    size = 0
                lines.append(f"- {item}: file_size={size} bytes, is_dir={is_dir}")

            return "\n".join(lines)
        except SecurityError as se:
            return f"Error: {se}"
        except Exception as e:
            return f"Error: {e}"


@default_registry.register
class GetFileContentTool(BaseTool):
    name = "get_file_content"
    description = "Reads the contents of a specified file relative to the working directory"
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path of the file to read, relative to the working directory",
            },
        },
        "required": ["file_path"],
    }

    def execute(self, working_directory: str = config.default_working_directory, file_path: str = "") -> str:
        if not file_path:
            return "Error: 'file_path' argument is required"
        try:
            target_path = resolve_safe_path(working_directory, file_path)
            if not os.path.isfile(target_path):
                return f'Error: File not found or is not a regular file: "{file_path}"'

            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(config.max_chars)
                if f.read(1):
                    content += f'[...File "{file_path}" truncated at {config.max_chars} characters]'

            return content
        except SecurityError as se:
            return f"Error: {se}"
        except Exception as e:
            return f"Error: {e}"


@default_registry.register
class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Writes or overwrites content to a specified file relative to the working directory"
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path of the file to write to, relative to the working directory",
            },
            "content": {
                "type": "string",
                "description": "The text content to write into the file",
            },
        },
        "required": ["file_path", "content"],
    }

    def execute(self, working_directory: str = config.default_working_directory, file_path: str = "", content: str = "") -> str:
        if not file_path:
            return "Error: 'file_path' argument is required"
        try:
            target_path = resolve_safe_path(working_directory, file_path)
            if os.path.isdir(target_path):
                return f'Error: Cannot write to "{file_path}" as it is a directory'

            parent_dir = os.path.dirname(target_path)
            os.makedirs(parent_dir, exist_ok=True)

            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)

            return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'
        except SecurityError as se:
            return f"Error: {se}"
        except Exception as e:
            return f"Error: {e}"
