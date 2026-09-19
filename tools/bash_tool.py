import os
import re
import subprocess
from typing import Any
from config import config
from harness.context import ObservationTrimmer
from tools.base import BaseTool
from tools.registry import default_registry
from tools.security import SecurityError, resolve_safe_path

FORBIDDEN_PATTERNS = [
    r"\brm\s+-[a-zA-Z0-9]*[rR][a-zA-Z0-9]*[fF][a-zA-Z0-9]*\s+(?:/|~|\$HOME|\.\.)(?:\s|$)",  # rm -rf / or ..
    r"\brm\s+-[rR][fF]\s+/",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # fork bomb
    r"\bmkfs\b",                      # disk format
    r"\bshutdown\b",
    r"\breboot\b",
    r"\binit\s+[06]\b",
    r"\bchmod\s+-[rR]\s+777\s+/(?:\s|$)",
    r"\bdd\s+if=.*\bof=/dev/",
    r"\b>\s*/dev/sd[a-z]",
]


@default_registry.register
class BashCommandTool(BaseTool):
    name = "bash_command"
    description = (
        "Executes a bash shell command in the working directory. "
        "Allows running tests (e.g. pytest), git commands, package management, or directory inspection. "
        "Commands are executed with safety sandboxing and a strict timeout."
    )
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute in the working directory",
            },
        },
        "required": ["command"],
    }

    def __init__(self, timeout_seconds: int | None = None) -> None:
        self.timeout_seconds = timeout_seconds or config.subprocess_timeout_seconds
        self.trimmer = ObservationTrimmer(max_chars=config.max_chars)

    def execute(
        self,
        working_directory: str = config.default_working_directory,
        command: str = "",
    ) -> str:
        if not command or not command.strip():
            return "Error: 'command' argument is required"

        command_str = command.strip()

        # Guardrail check against catastrophic commands
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, command_str):
                return f"Error: Command blocked by harness security guardrail: '{pattern}' is prohibited."

        try:
            working_dir_abs = os.path.abspath(working_directory)
            if not os.path.isdir(working_dir_abs):
                return f'Error: Working directory "{working_directory}" does not exist'

            process = subprocess.run(
                command_str,
                cwd=working_dir_abs,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )

            output_parts = []
            if process.returncode != 0:
                output_parts.append(f"Exit code: {process.returncode}")

            if not process.stdout and not process.stderr:
                output_parts.append("Command completed with no output.")
            else:
                if process.stdout:
                    output_parts.append(f"STDOUT:\n{process.stdout}")
                if process.stderr:
                    output_parts.append(f"STDERR:\n{process.stderr}")

            combined_output = "\n".join(output_parts)
            return self.trimmer.trim(combined_output, label=f"Command '{command_str}'")

        except subprocess.TimeoutExpired as e:
            timeout_msg = [
                f"Error: Command timed out after {self.timeout_seconds} seconds: '{command_str}'"
            ]
            if e.stdout:
                stdout_str = e.stdout if isinstance(e.stdout, str) else e.stdout.decode("utf-8", errors="replace")
                timeout_msg.append(f"STDOUT:\n{stdout_str}")
            if e.stderr:
                stderr_str = e.stderr if isinstance(e.stderr, str) else e.stderr.decode("utf-8", errors="replace")
                timeout_msg.append(f"STDERR:\n{stderr_str}")
            return "\n".join(timeout_msg)
        except Exception as e:
            return f"Error executing bash command: {e}"
