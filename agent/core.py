import sys
from dataclasses import dataclass
from typing import Callable
from google.genai import types
from config import config
from llm.base import BaseLLMClient
from llm.gemini import GeminiLLMClient
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
        self.llm_client = llm_client or GeminiLLMClient()
        self.registry = registry or default_registry
        self.system_prompt = system_prompt
        self.working_directory = working_directory
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.verbose = verbose
        self.log = log_callback or (lambda msg: print(msg))

    def run(self, prompt: str) -> AgentResult:
        """Runs the agent loop for the given user prompt."""
        messages: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            )
        ]

        total_prompt_tokens = 0
        total_response_tokens = 0

        for iteration in range(self.max_iterations):
            response = self.llm_client.generate_content(
                contents=messages,
                tools=[self.registry.to_genai_tool()],
                system_instruction=self.system_prompt,
                temperature=self.temperature,
            )

            if response.usage_metadata:
                p_tokens = response.usage_metadata.prompt_token_count or 0
                r_tokens = response.usage_metadata.candidates_token_count or 0
                total_prompt_tokens += p_tokens
                total_response_tokens += r_tokens

                if self.verbose:
                    self.log(f"\n--- Iteration {iteration + 1} ---")
                    self.log(f"User prompt: {prompt}")
                    self.log(f"Prompt tokens: {p_tokens}")
                    self.log(f"Response tokens: {r_tokens}")

            if response.candidates and response.candidates[0].content:
                messages.append(response.candidates[0].content)

            if response.function_calls:
                function_results: list[types.Part] = []

                for function_call in response.function_calls:
                    fn_name = function_call.name or ""
                    fn_args = dict(function_call.args) if function_call.args else {}
                    fn_args["working_directory"] = self.working_directory

                    if self.verbose:
                        self.log(f"Calling function: {fn_name}({function_call.args})")
                    else:
                        self.log(f" - Calling function: {fn_name}")

                    raw_result = self.registry.execute(fn_name, **fn_args)

                    if self.verbose:
                        self.log(f"-> {raw_result}")

                    part = types.Part.from_function_response(
                        name=fn_name,
                        response={"result": raw_result},
                    )
                    function_results.append(part)

                messages.append(types.Content(role="user", parts=function_results))

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
