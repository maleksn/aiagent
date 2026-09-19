import argparse
import sys
from config import config
from agent.core import Agent
from llm.openrouter import OpenRouterLLMClient
from harness.guardrails import BudgetGuard, BudgetConfig
from harness.telemetry import TrajectoryRecorder


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous Software Engineering Agent with Harness")
    parser.add_argument(
        "user_prompt",
        type=str,
        nargs="?",
        default=None,
        help="User prompt or task description (omit for interactive mode)",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Start interactive conversational session",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose execution logs")
    parser.add_argument("--trace", action="store_true", help="Enable step-by-step harness tracing")
    parser.add_argument(
        "--replay",
        type=str,
        default=None,
        help="Replay a previously recorded trajectory JSONL file",
    )
    parser.add_argument(
        "--working-dir",
        type=str,
        default=config.default_working_directory,
        help=f"Working directory for the agent (default: {config.default_working_directory})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=config.default_model,
        help=f"LLM model to use on OpenRouter (default: {config.default_model})",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=100_000,
        help="Maximum total token budget for the session",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        default=2.0,
        help="Maximum cost budget in USD for the session",
    )
    args = parser.parse_args()

    # Replay mode
    if args.replay:
        TrajectoryRecorder.replay(args.replay)
        sys.exit(0)

    llm_client = OpenRouterLLMClient(model=args.model)
    budget_guard = BudgetGuard(
        BudgetConfig(
            max_iterations=config.max_iterations,
            max_total_tokens=args.max_tokens,
            max_cost_usd=args.max_cost,
        )
    )

    verbose = args.verbose or args.trace
    agent = Agent(
        llm_client=llm_client,
        working_directory=args.working_dir,
        max_iterations=config.max_iterations,
        verbose=verbose,
        budget_guard=budget_guard,
    )

    # Interactive REPL mode
    if args.interactive or not args.user_prompt:
        print(f"=== Autonomous Software Engineering Agent (Harness Enabled) ===")
        print(f"Model: {args.model}")
        print(f"Working Directory: {args.working_dir}")
        print("Type 'exit' or 'quit' to end the session.\n")

        while True:
            try:
                prompt = input("agent> ").strip()
                if not prompt:
                    continue
                if prompt.lower() in ("exit", "quit", "q"):
                    print("Goodbye!")
                    break

                result = agent.run(prompt)
                if result.success:
                    if result.final_text:
                        print(f"\n{result.final_text}\n")
                    if args.trace:
                        print(f"[Telemetry] Trajectory: {result.trajectory_path} | Cost: ${result.estimated_cost_usd:.4f}")
                else:
                    print(f"\nError: {result.error}\n", file=sys.stderr)
            except (KeyboardInterrupt, EOFError):
                print("\nSession interrupted. Goodbye!")
                break
        sys.exit(0)

    # Single-shot mode
    result = agent.run(args.user_prompt)

    if result.success:
        if result.final_text:
            print(result.final_text)
        if args.trace or args.verbose:
            print(f"\n[Telemetry] Trajectory: {result.trajectory_path} | Cost: ${result.estimated_cost_usd:.4f}", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        if result.trajectory_path:
            print(f"[Telemetry] Failed run trajectory: {result.trajectory_path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
