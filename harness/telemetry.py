import datetime
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TrajectoryStep:
    iteration: int
    timestamp: str
    prompt_tokens: int
    completion_tokens: int
    assistant_text: str | None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)


class TrajectoryRecorder:
    """
    Records complete agent session trajectories into structured JSONL files.
    Allows replaying, auditing, debugging, and evaluating agent actions.
    """

    def __init__(
        self,
        output_dir: str = ".trajectories",
        run_id: str | None = None,
    ) -> None:
        self.output_dir = output_dir
        self.run_id = run_id or f"run_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.trajectory_path = os.path.join(self.output_dir, f"{self.run_id}.jsonl")
        self.steps: list[TrajectoryStep] = []
        self._initialized = False

    def initialize_session(self, prompt: str, model: str, working_directory: str) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        init_event = {
            "event": "session_start",
            "run_id": self.run_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "prompt": prompt,
            "model": model,
            "working_directory": working_directory,
        }
        with open(self.trajectory_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(init_event) + "\n")
        self._initialized = True

    def record_step(self, step: TrajectoryStep) -> None:
        self.steps.append(step)
        if self._initialized:
            event = {
                "event": "step",
                "run_id": self.run_id,
                **asdict(step),
            }
            with open(self.trajectory_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

    def finalize_session(
        self,
        success: bool,
        final_text: str | None,
        total_iterations: int,
        total_prompt_tokens: int,
        total_response_tokens: int,
        estimated_cost_usd: float = 0.0,
        error: str | None = None,
    ) -> None:
        if self._initialized:
            final_event = {
                "event": "session_end",
                "run_id": self.run_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "success": success,
                "final_text": final_text,
                "total_iterations": total_iterations,
                "total_prompt_tokens": total_prompt_tokens,
                "total_response_tokens": total_response_tokens,
                "total_tokens": total_prompt_tokens + total_response_tokens,
                "estimated_cost_usd": estimated_cost_usd,
                "error": error,
            }
            with open(self.trajectory_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(final_event) + "\n")

    @staticmethod
    def replay(file_path: str) -> None:
        """Prints a human-readable playback of a recorded trajectory."""
        if not os.path.isfile(file_path):
            print(f"Trajectory file not found: {file_path}")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        print(f"\n{'='*60}")
        print(f" REPLAYING TRAJECTORY: {os.path.basename(file_path)}")
        print(f"{'='*60}\n")

        for line in lines:
            if not line.strip():
                continue
            data = json.loads(line)
            event = data.get("event")

            if event == "session_start":
                print(f"Prompt: {data.get('prompt')}")
                print(f"Model: {data.get('model')}")
                print(f"Working Dir: {data.get('working_directory')}\n")
            elif event == "step":
                print(f"--- Iteration {data.get('iteration')} ---")
                if data.get("assistant_text"):
                    print(f"Assistant: {data.get('assistant_text')}")
                for tc in data.get("tool_calls", []):
                    print(f" -> Call Tool: {tc.get('name')}({tc.get('args')})")
                for tr in data.get("tool_results", []):
                    res_preview = str(tr.get("result", ""))[:200].replace("\n", " ")
                    print(f" <- Tool Result: {res_preview}...")
                print("")
            elif event == "session_end":
                print(f"{'='*60}")
                print(f"Outcome: {'SUCCESS' if data.get('success') else 'FAILED'}")
                print(f"Total Iterations: {data.get('total_iterations')}")
                print(f"Total Tokens: {data.get('total_tokens')}")
                print(f"Estimated Cost: ${data.get('estimated_cost_usd', 0.0):.4f}")
                if data.get("error"):
                    print(f"Error: {data.get('error')}")
                if data.get("final_text"):
                    print(f"Final Text:\n{data.get('final_text')}")
                print(f"{'='*60}\n")
