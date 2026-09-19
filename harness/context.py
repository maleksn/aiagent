import re
from typing import Any


class ObservationTrimmer:
    """
    Intelligently trims tool outputs and observations to protect the model's
    context window from exploding while preserving critical diagnostic info
    (e.g., initial command/context at the head and error stack traces at the tail).
    """

    def __init__(
        self,
        max_chars: int = 8000,
        head_lines: int = 25,
        tail_lines: int = 35,
    ) -> None:
        self.max_chars = max_chars
        self.head_lines = head_lines
        self.tail_lines = tail_lines

    def trim(self, text: str, label: str = "Output") -> str:
        """
        Trims text if it exceeds max_chars.
        Preserves head and tail lines to keep both context and concluding stack traces.
        """
        if not text or len(text) <= self.max_chars:
            return text

        lines = text.splitlines(keepends=True)
        total_lines = len(lines)

        # If lines are few but individual lines are huge, or normal multi-line output
        if total_lines <= (self.head_lines + self.tail_lines):
            # Fallback to direct character slice with tail preservation
            half_chars = (self.max_chars - 200) // 2
            omitted = len(text) - (half_chars * 2)
            return (
                f"{text[:half_chars]}\n"
                f"[... {label} truncated: omitted {omitted} characters ...]\n"
                f"{text[-half_chars:]}"
            )

        head = "".join(lines[: self.head_lines])
        tail = "".join(lines[-self.tail_lines :])
        omitted_lines = total_lines - (self.head_lines + self.tail_lines)
        omitted_chars = len(text) - (len(head) + len(tail))

        marker = (
            f"\n[... {label} truncated: omitted {omitted_lines} lines "
            f"({omitted_chars} chars) ...]\n"
        )
        return f"{head}{marker}{tail}"

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Approximates token count based on a 4-character per token heuristic."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    @classmethod
    def compact_messages(
        cls,
        messages: list[dict[str, Any]],
        max_total_chars: int = 60000,
        keep_recent_turns: int = 4,
    ) -> list[dict[str, Any]]:
        """
        If messages exceed total char budget, trims older tool observations
        while keeping recent turns and initial user prompt intact.
        """
        total_chars = sum(len(str(m.get("content") or "")) for m in messages)
        if total_chars <= max_total_chars or len(messages) <= keep_recent_turns:
            return messages

        compacted = list(messages)
        # Protect user prompt (index 0) and the most recent N messages
        cutoff_idx = max(1, len(compacted) - keep_recent_turns)

        trimmer = cls(max_chars=1000, head_lines=5, tail_lines=5)

        for i in range(1, cutoff_idx):
            msg = compacted[i]
            if msg.get("role") == "tool" and isinstance(msg.get("content"), str):
                msg_content = msg["content"]
                if len(msg_content) > 1000:
                    compacted[i] = {
                        **msg,
                        "content": trimmer.trim(msg_content, label="Archived observation"),
                    }

        return compacted
