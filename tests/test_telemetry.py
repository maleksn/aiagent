import os
import json
from harness.telemetry import TrajectoryRecorder, TrajectoryStep


def test_trajectory_recorder_flow(tmp_path):
    output_dir = tmp_path / "trajectories"
    recorder = TrajectoryRecorder(output_dir=str(output_dir), run_id="test_run_123")

    recorder.initialize_session(
        prompt="Fix the bug",
        model="test-model",
        working_directory="/test/dir",
    )

    recorder.record_step(
        TrajectoryStep(
            iteration=1,
            timestamp="2026-09-19T20:00:00",
            prompt_tokens=10,
            completion_tokens=5,
            assistant_text="I will check files.",
            tool_calls=[{"id": "c1", "name": "get_files_info", "args": {}}],
            tool_results=[{"name": "get_files_info", "result": "main.py"}],
        )
    )

    recorder.finalize_session(
        success=True,
        final_text="Fixed cleanly.",
        total_iterations=1,
        total_prompt_tokens=10,
        total_response_tokens=5,
        estimated_cost_usd=0.0001,
    )

    trajectory_file = output_dir / "test_run_123.jsonl"
    assert trajectory_file.exists()

    with open(trajectory_file, "r") as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 3
    assert events[0]["event"] == "session_start"
    assert events[0]["prompt"] == "Fix the bug"
    assert events[1]["event"] == "step"
    assert events[1]["iteration"] == 1
    assert events[2]["event"] == "session_end"
    assert events[2]["success"] is True
    assert events[2]["total_tokens"] == 15
