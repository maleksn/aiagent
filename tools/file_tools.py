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
    description = (
        "Reads the contents of a specified file relative to the working directory. "
        "Supports optional start_line and end_line parameters for reading specific sections."
    )
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path of the file to read, relative to the working directory",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional 1-based start line number to read from",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional 1-based end line number to read until (inclusive)",
            },
        },
        "required": ["file_path"],
    }

    def execute(
        self,
        working_directory: str = config.default_working_directory,
        file_path: str = "",
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        if not file_path:
            return "Error: 'file_path' argument is required"
        try:
            target_path = resolve_safe_path(working_directory, file_path)
            if not os.path.isfile(target_path):
                return f'Error: File not found or is not a regular file: "{file_path}"'

            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            if start_line is not None or end_line is not None:
                s = max(1, start_line) if start_line is not None else 1
                e = min(total_lines, end_line) if end_line is not None else total_lines
                if s > total_lines:
                    return f'Error: start_line ({s}) exceeds total lines in file ({total_lines})'
                selected_lines = lines[s - 1 : e]
                content = "".join(f"{s + i}: {line}" for i, line in enumerate(selected_lines))
                return content

            content = "".join(lines)
            if len(content) > config.max_chars:
                content = content[: config.max_chars] + f'\n[...File "{file_path}" truncated at {config.max_chars} characters]'

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


@default_registry.register
class EditFileTool(BaseTool):
    name = "edit_file"
    description = (
        "Edits a file by replacing an exact, unique block of text (target_content) "
        "with new text (replacement_content). Avoids having to rewrite the whole file."
    )
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path of the file to edit, relative to the working directory",
            },
            "target_content": {
                "type": "string",
                "description": "The exact existing text block to be replaced (must match uniquely in the file)",
            },
            "replacement_content": {
                "type": "string",
                "description": "The replacement text to insert in place of target_content",
            },
        },
        "required": ["file_path", "target_content", "replacement_content"],
    }

    def execute(
        self,
        working_directory: str = config.default_working_directory,
        file_path: str = "",
        target_content: str = "",
        replacement_content: str = "",
    ) -> str:
        if not file_path:
            return "Error: 'file_path' argument is required"
        if not target_content:
            return "Error: 'target_content' cannot be empty"

        try:
            target_path = resolve_safe_path(working_directory, file_path)
            if not os.path.isfile(target_path):
                return f'Error: File not found or is not a regular file: "{file_path}"'

            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()

            count = content.count(target_content)
            if count == 0:
                return f'Error: target_content not found in "{file_path}"'
            if count > 1:
                return (
                    f'Error: target_content appears {count} times in "{file_path}". '
                    f'It must match uniquely. Please include more surrounding context.'
                )

            new_content = content.replace(target_content, replacement_content, 1)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return f'Successfully edited "{file_path}" (replaced 1 occurrence)'
        except SecurityError as se:
            return f"Error: {se}"
        except Exception as e:
            return f"Error: {e}"

