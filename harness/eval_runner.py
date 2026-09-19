import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agent.core import Agent
from llm.base import BaseLLMClient
from llm.openrouter import OpenRouterLLMClient


@dataclass
class EvalTaskResult:
    task_id: str
    task_name: str
    passed: bool
    iterations: int
    tokens: int
    cost_usd: float
    duration_seconds: float
    error: str | None = None


class EvalHarnessRunner:
    """
    Automated evaluation harness for benchmarking coding agent performance,
    reproducibility, token efficiency, and task success rate (pass@1).
    """

    def __init__(
        self,
        tasks_path: str = "evals/tasks.json",
        llm_client: BaseLLMClient | None = None,
        max_iterations: int = 15,
    ) -> None:
        self.tasks_path = tasks_path
        self.llm_client = llm_client
        self.max_iterations = max_iterations

    def load_tasks(self) -> list[dict]:
        if not os.path.isfile(self.tasks_path):
            raise FileNotFoundError(f"Tasks file not found: {self.tasks_path}")
        with open(self.tasks_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_task(self, task: dict, dry_run: bool = False) -> EvalTaskResult:
        task_id = task["id"]
        task_name = task.get("name", task_id)
        prompt = task["prompt"]
        template_dir = task.get("working_dir_template", "calculator")
        verification_cmd = task.get("verification_command", "python tests.py")
        expected_code = task.get("expected_exit_code", 0)

        start_t = time.time()

        if dry_run:
            return EvalTaskResult(
                task_id=task_id,
                task_name=task_name,
                passed=True,
                iterations=1,
                tokens=100,
                cost_usd=0.0001,
                duration_seconds=0.01,
            )

        if not os.path.isabs(template_dir):
            template_dir = os.path.abspath(template_dir)

        # Create isolated workspace sandbox
        with tempfile.TemporaryDirectory(prefix=f"eval_{task_id}_") as sandbox_dir:
            if os.path.isdir(template_dir):
                shutil.copytree(template_dir, sandbox_dir, dirs_exist_ok=True)

            client = self.llm_client or OpenRouterLLMClient()
            agent = Agent(
                llm_client=client,
                working_directory=sandbox_dir,
                max_iterations=self.max_iterations,
                verbose=False,
            )

            agent_res = agent.run(prompt)

            # Verification pass
            verify_proc = subprocess.run(
                verification_cmd,
                cwd=sandbox_dir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            passed = (verify_proc.returncode == expected_code)
            duration = time.time() - start_t

            err = None
            if not passed:
                err = f"Verification failed (code {verify_proc.returncode}):\n{verify_proc.stderr or verify_proc.stdout}"

            return EvalTaskResult(
                task_id=task_id,
                task_name=task_name,
                passed=passed,
                iterations=agent_res.total_iterations,
                tokens=agent_res.total_prompt_tokens + agent_res.total_response_tokens,
                cost_usd=agent_res.estimated_cost_usd,
                duration_seconds=duration,
                error=err,
            )

    def run_all(self, dry_run: bool = False, verbose: bool = True) -> list[EvalTaskResult]:
        tasks = self.load_tasks()
        results: list[EvalTaskResult] = []

        if verbose:
            print(f"\n=======================================================")
            print(f" AGENT EVALUATION HARNESS BENCHMARK ({len(tasks)} tasks)")
            print(f"=======================================================\n")

        for idx, task in enumerate(tasks, start=1):
            if verbose:
                print(f"[{idx}/{len(tasks)}] Running: {task.get('name', task['id'])}...", end="", flush=True)
            res = self.run_task(task, dry_run=dry_run)
            status_badge = "PASSED" if res.passed else "FAILED"
            if verbose:
                print(f" -> {status_badge} ({res.duration_seconds:.1f}s, {res.tokens} tokens, ${res.cost_usd:.4f})")
            results.append(res)

        if verbose:
            self.print_summary(results)
        return results

    @staticmethod
    def print_summary(results: list[EvalTaskResult]) -> None:
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        total_tokens = sum(r.tokens for r in results)
        total_cost = sum(r.cost_usd for r in results)
        total_time = sum(r.duration_seconds for r in results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"\n{'='*70}")
        print(f" BENCHMARK SUMMARY SCORECARD")
        print(f"{'='*70}")
        print(f"Pass Rate:        {passed}/{total} ({pass_rate:.1f}%)")
        print(f"Total Time:       {total_time:.1f}s")
        print(f"Total Tokens:     {total_tokens:,}")
        print(f"Total Cost (USD): ${total_cost:.4f}")
        print(f"{'='*70}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Coding Agent Evaluation Harness")
    parser.add_argument(
        "--tasks",
        type=str,
        default="evals/tasks.json",
        help="Path to evaluation tasks JSON file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run harness in dry-run mode without invoking LLM",
    )
    args = parser.parse_args()

    runner = EvalHarnessRunner(tasks_path=args.tasks)
    results = runner.run_all(dry_run=args.dry_run)
    all_passed = all(r.passed for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
