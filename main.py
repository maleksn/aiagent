import argparse
import sys
from config import config
from agent.core import Agent
from llm.openrouter import OpenRouterLLMClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous Software Engineering Agent")
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
    args = parser.parse_args()

    llm_client = OpenRouterLLMClient(model=args.model)
    agent = Agent(
        llm_client=llm_client,
        working_directory=args.working_dir,
        verbose=args.verbose,
    )

    # Interactive REPL mode
    if args.interactive or not args.user_prompt:
        print(f"=== Autonomous Software Engineering Agent (OpenRouter) ===")
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
        sys.exit(0)
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        sys.exit(1)



if __name__ == "__main__":
    main()
