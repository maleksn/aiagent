import json
from harness.eval_runner import EvalHarnessRunner, EvalTaskResult


def test_eval_runner_dry_run(tmp_path):
    tasks_file = tmp_path / "tasks.json"
    tasks_data = [
        {
            "id": "mock_task",
            "name": "Mock Task",
            "prompt": "Do nothing",
            "working_dir_template": "calculator",
            "verification_command": "true",
            "expected_exit_code": 0,
        }
    ]
    tasks_file.write_text(json.dumps(tasks_data))

    runner = EvalHarnessRunner(tasks_path=str(tasks_file))
    results = runner.run_all(dry_run=True, verbose=False)

    assert len(results) == 1
    assert results[0].task_id == "mock_task"
    assert results[0].passed is True
    assert results[0].cost_usd > 0
