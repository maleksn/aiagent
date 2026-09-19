import json
from dataclasses import dataclass
from typing import Any, Callable
from config import config
from llm.base import BaseLLMClient, ToolCall
from llm.openrouter import OpenRouterLLMClient
from tools.registry import ToolRegistry, default_registry
from prompts import system_prompt as default_system_prompt


@dataclass
class AgentResult:
    """Encapsulates the final outcome of an agent run."""
    success: bool
    final_text: str | None
    total_iterations: int
    total_prompt_tokens: int = 0
    total_response_tokens: int = 0
    error: str | None = None


class Agent:
    """
    Autonomous AI Software Engineering Agent.
    Coordinates LLM interactions and tool executions.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        registry: ToolRegistry | None = None,
        system_prompt: str = default_system_prompt,
        working_directory: str = config.default_working_directory,
        max_iterations: int = config.max_iterations,
        temperature: float = config.temperature,
        verbose: bool = False,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.llm_client = llm_client or OpenRouterLLMClient()
        self.registry = registry or default_registry
        self.system_prompt = system_prompt
        self.working_directory = working_directory
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.verbose = verbose
        self.log = log_callback or (lambda msg: print(msg))

    def run(self, prompt: str) -> AgentResult:
        """Runs the agent loop for the given user prompt."""
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": prompt}
        ]

        total_prompt_tokens = 0
        total_response_tokens = 0

        for iteration in range(self.max_iterations):
            try:
                response = self.llm_client.generate_content(
                    messages=messages,
                    tools=self.registry.to_tools(),
                    system_instruction=self.system_prompt,
                    temperature=self.temperature,
                )
            except Exception as e:
                return AgentResult(
                    success=False,
                    final_text=None,
                    total_iterations=iteration + 1,
                    total_prompt_tokens=total_prompt_tokens,
                    total_response_tokens=total_response_tokens,
                    error=f"LLM generation failed: {e}",
                )

            total_prompt_tokens += response.prompt_tokens
            total_response_tokens += response.completion_tokens

            if self.verbose:
                self.log(f"\n--- Iteration {iteration + 1} ---")
                self.log(f"User prompt: {prompt}")
                self.log(f"Prompt tokens: {response.prompt_tokens}")
                self.log(f"Response tokens: {response.completion_tokens}")

            if response.has_tool_calls:
                # Record assistant message with tool calls
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": (
                                    json.dumps(tc.args)
                                    if isinstance(tc.args, dict)
                                    else str(tc.args)
                                ),
                            },
                        }
                        for tc in response.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                for tc in response.tool_calls:
                    fn_name = tc.name
                    fn_args = dict(tc.args) if tc.args else {}
                    fn_args["working_directory"] = self.working_directory

                    if self.verbose:
                        self.log(f"Calling function: {fn_name}({tc.args})")
                    else:
                        self.log(f" - Calling function: {fn_name}")

                    raw_result = self.registry.execute(fn_name, **fn_args)

                    if self.verbose:
                        self.log(f"-> {raw_result}")

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": fn_name,
                            "content": str(raw_result),
                        }
                    )
            else:
                final_text = response.text or ""
                return AgentResult(
                    success=True,
                    final_text=final_text,
                    total_iterations=iteration + 1,
                    total_prompt_tokens=total_prompt_tokens,
                    total_response_tokens=total_response_tokens,
                )

        return AgentResult(
            success=False,
            final_text=None,
            total_iterations=self.max_iterations,
            total_prompt_tokens=total_prompt_tokens,
            total_response_tokens=total_response_tokens,
            error=f"Agent reached the maximum iteration limit ({self.max_iterations}) without finishing.",
        )
