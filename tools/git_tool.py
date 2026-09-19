import os
import subprocess
from typing import Any
from config import config
from harness.context import ObservationTrimmer
from tools.base import BaseTool
from tools.registry import default_registry


def _run_git(working_dir: str, args: list[str]) -> tuple[int, str, str]:
    """Helper to run a git command inside the given working directory."""
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=os.path.abspath(working_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return -1, "", str(e)


@default_registry.register
class GitStatusTool(BaseTool):
    name = "git_status"
    description = (
        "Shows the current working tree status (git status --short). "
        "Useful for verifying which files have been modified, created, or deleted."
    )
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
    }

    def execute(self, working_directory: str = config.default_working_directory, **kwargs) -> str:
        code, stdout, stderr = _run_git(working_directory, ["status", "--short"])
        if code != 0:
            return f"Error running git status: {stderr or stdout}"
        if not stdout.strip():
            return "Git working directory is clean (no modified or untracked files)."
        return f"Git Status:\n{stdout.strip()}"


@default_registry.register
class GitDiffTool(BaseTool):
    name = "git_diff"
    description = (
        "Inspects git diff of current changes against HEAD or a specific file. "
        "Allows the agent to review surgical line-by-line diffs before finishing."
    )
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Optional specific file to diff relative to working directory",
            },
        },
    }

    def __init__(self) -> None:
        self.trimmer = ObservationTrimmer(max_chars=config.max_chars)

    def execute(
        self,
        working_directory: str = config.default_working_directory,
        file_path: str | None = None,
        **kwargs,
    ) -> str:
        args = ["diff"]
        if file_path:
            args.extend(["--", file_path])

        code, stdout, stderr = _run_git(working_directory, args)
        if code != 0:
            return f"Error running git diff: {stderr or stdout}"
        if not stdout.strip():
            return "No changes detected in git diff."
        return self.trimmer.trim(stdout, label="Git Diff")


@default_registry.register
class GitCheckpointTool(BaseTool):
    name = "git_checkpoint"
    description = (
        "Manages workspace safety snapshots. Actions: 'save' (stash uncommitted work with a tag) "
        "or 'restore' (revert uncommitted changes back to clean state)."
    )
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["save", "restore"],
                "description": "'save' creates a safety stash; 'restore' reverts working directory to previous state",
            },
            "tag": {
                "type": "string",
                "description": "Optional label for the checkpoint",
            },
        },
        "required": ["action"],
    }

    def execute(
        self,
        working_directory: str = config.default_working_directory,
        action: str = "save",
        tag: str = "agent-checkpoint",
        **kwargs,
    ) -> str:
        if action == "save":
            code, stdout, stderr = _run_git(
                working_directory, ["stash", "push", "-u", "-m", f"harness-checkpoint:{tag}"]
            )
            if code != 0:
                return f"Error creating checkpoint: {stderr or stdout}"
            # Also restore the stash to keep working copy active while recorded
            _run_git(working_directory, ["stash", "apply"])
            return f"Checkpoint '{tag}' successfully recorded."
        elif action == "restore":
            code, stdout, stderr = _run_git(working_directory, ["checkout", "."])
            _run_git(working_directory, ["clean", "-fd"])
            if code != 0:
                return f"Error restoring checkpoint: {stderr or stdout}"
            return "Working directory successfully restored to clean git state."
        else:
            return f"Error: Unknown action '{action}'. Use 'save' or 'restore'."
