import fnmatch
import os
from typing import Any
from config import config
from tools.base import BaseTool
from tools.registry import default_registry
from tools.security import SecurityError, resolve_safe_path

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".agents",
    ".mypy_cache",
}


@default_registry.register
class SearchInFilesTool(BaseTool):
    name = "search_in_files"
    description = (
        "Searches for a text query across files in a specified directory (grep-like). "
        "Returns file paths, line numbers, and matching lines."
    )
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The text pattern to search for",
            },
            "directory": {
                "type": "string",
                "description": "Subdirectory to search in, relative to the working directory (default is '.')",
            },
            "file_pattern": {
                "type": "string",
                "description": "Optional glob pattern to filter files, e.g. '*.py' or '*.txt'",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether to perform a case-sensitive search (default is false)",
            },
        },
        "required": ["query"],
    }

    def execute(
        self,
        working_directory: str = config.default_working_directory,
        query: str = "",
        directory: str = ".",
        file_pattern: str | None = None,
        case_sensitive: bool = False,
    ) -> str:
        if not query:
            return "Error: 'query' argument is required"

        try:
            target_dir = resolve_safe_path(working_directory, directory)
            if not os.path.isdir(target_dir):
                return f'Error: "{directory}" is not a directory'

            matches: list[str] = []
            max_matches = 50
            search_query = query if case_sensitive else query.lower()

            for root, dirs, files in os.walk(target_dir):
                # Filter out ignored directories in-place
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

                for file in files:
                    if file_pattern and not fnmatch.fnmatch(file, file_pattern):
                        continue

                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, target_dir)

                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line_idx, line in enumerate(f, start=1):
                                line_to_check = line if case_sensitive else line.lower()
                                if search_query in line_to_check:
                                    matches.append(
                                        f"{rel_path}:{line_idx}: {line.rstrip()}"
                                    )
                                    if len(matches) >= max_matches:
                                        break
                    except (OSError, UnicodeError):
                        continue

                    if len(matches) >= max_matches:
                        break
                if len(matches) >= max_matches:
                    break

            if not matches:
                return f'No matches found for query "{query}"'

            result_str = "\n".join(matches)
            if len(matches) >= max_matches:
                result_str += f"\n[Results capped at {max_matches} matches]"
            return result_str

        except SecurityError as se:
            return f"Error: {se}"
        except Exception as e:
            return f"Error: {e}"
