import os
import subprocess
import sys
from typing import Any
from config import config
from tools.base import BaseTool
from tools.registry import default_registry
from tools.security import SecurityError, resolve_safe_path


@default_registry.register
class RunPythonFileTool(BaseTool):
    name = "run_python_file"
    description = "Executes a specified Python file with optional arguments"
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The path of the Python file to run, relative to the working directory",
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of command-line arguments to pass to the Python script",
            },
        },
        "required": ["file_path"],
    }

    def execute(
        self,
        working_directory: str = config.default_working_directory,
        file_path: str = "",
        args: list[str] | None = None,
    ) -> str:
        if not file_path:
            return "Error: 'file_path' argument is required"

        try:
            working_dir_abs = os.path.abspath(working_directory)
            target_path = resolve_safe_path(working_directory, file_path)

            if not os.path.isfile(target_path):
                return f'Error: "{file_path}" does not exist or is not a regular file'

            if not file_path.lower().endswith(".py"):
                return f'Error: "{file_path}" is not a Python file'

            command = [sys.executable, target_path]
            if args:
                command.extend(args)

            process = subprocess.run(
                command,
                cwd=working_dir_abs,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=config.subprocess_timeout_seconds,
            )

            output_parts = []
            if process.returncode != 0:
                output_parts.append(f"Process exited with code {process.returncode}")

            if not process.stdout and not process.stderr:
                output_parts.append("No output produced")
            else:
                if process.stdout:
                    output_parts.append(f"STDOUT:\n{process.stdout}")
                if process.stderr:
                    output_parts.append(f"STDERR:\n{process.stderr}")

            return "\n".join(output_parts)

        except SecurityError as se:
            return f"Error: {se}"
        except subprocess.TimeoutExpired as e:
            timeout_msg = [
                f"Error: executing Python file: Process timed out after {config.subprocess_timeout_seconds} seconds"
            ]
            if e.stdout:
                stdout_str = (
                    e.stdout
                    if isinstance(e.stdout, str)
                    else e.stdout.decode("utf-8", errors="replace")
                )
                timeout_msg.append(f"STDOUT:\n{stdout_str}")
            if e.stderr:
                stderr_str = (
                    e.stderr
                    if isinstance(e.stderr, str)
                    else e.stderr.decode("utf-8", errors="replace")
                )
                timeout_msg.append(f"STDERR:\n{stderr_str}")
            return "\n".join(timeout_msg)
        except Exception as e:
            return f"Error executing Python file: {e}"
