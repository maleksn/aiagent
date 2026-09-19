import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolExecutionRecord:
    name: str
    args: dict[str, Any]
    result: str


class LoopDetector:
    """
    Detects when an agent enters repetitive cycles or infinite loops
    (e.g., executing the exact same tool call multiple times consecutively).
    Generates steering intervention messages to help the model self-correct.
    """

    def __init__(self, repetition_threshold: int = 3) -> None:
        self.repetition_threshold = repetition_threshold
        self.history: list[ToolExecutionRecord] = []

    def record_and_check(self, name: str, args: dict[str, Any], result: str) -> str | None:
        """
        Records a tool execution and checks if the agent is stuck in a loop.
        Returns a steering intervention message if a loop is detected, or None otherwise.
        """
        cleaned_args = {k: v for k, v in args.items() if k != "working_directory"}
        record = ToolExecutionRecord(name=name, args=cleaned_args, result=result)
        self.history.append(record)

        # Check consecutive identical tool calls
        consecutive_count = 0
        target_args_str = json.dumps(cleaned_args, sort_keys=True)

        for prev in reversed(self.history):
            prev_args_str = json.dumps(prev.args, sort_keys=True)
            if prev.name == name and prev_args_str == target_args_str:
                consecutive_count += 1
            else:
                break

        if consecutive_count >= self.repetition_threshold:
            short_res = result[:150].replace("\n", " ")
            return (
                f"[HARNESS STEERING INTERVENTION]: You have invoked tool '{name}' "
                f"with identical arguments {consecutive_count} times in a row without progress. "
                f"Previous output was: '{short_res}...'. "
                f"DO NOT repeat this call. Step back, re-assess your hypothesis, check other files "
                f"or error logs, or try a different strategy to achieve the user's objective."
            )

        return None

    @staticmethod
    def enrich_error(tool_name: str, error_msg: str) -> str:
        """
        Enhances raw tool error strings with actionable hints for the model.
        """
        msg_lower = error_msg.lower()

        if "does not exist" in msg_lower or "file not found" in msg_lower:
            return (
                f"{error_msg}\n"
                f"[Harness Hint: Use 'get_files_info' or 'search_in_files' "
                f"to verify the exact file name and directory structure.]"
            )
        if "target_content not found" in msg_lower:
            return (
                f"{error_msg}\n"
                f"[Harness Hint: Read the file first using 'get_file_content' to ensure the exact "
                f"indentation and character sequence matches target_content.]"
            )
        if "appears" in msg_lower and "times" in msg_lower:
            return (
                f"{error_msg}\n"
                f"[Harness Hint: Include more unique surrounding lines in 'target_content' so it "
                f"matches exactly one location.]"
            )
        return error_msg
