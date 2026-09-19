import argparse
import sys
from config import config
from agent.core import Agent
from llm.gemini import GeminiLLMClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous Software Engineering Agent")
    parser.add_argument("user_prompt", type=str, help="User prompt or task description")
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
        help=f"LLM model to use (default: {config.default_model})",
    )
    args = parser.parse_args()

    llm_client = GeminiLLMClient(model=args.model)
    agent = Agent(
        llm_client=llm_client,
        working_directory=args.working_dir,
        verbose=args.verbose,
    )

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
