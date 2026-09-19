import json
from dataclasses import dataclass
from typing import Any, Callable
from config import config
from llm.base import BaseLLMClient, ToolCall
from llm.openrouter import OpenRouterLLMClient
from tools.registry import ToolRegistry, default_registry
from prompts import system_prompt as default_system_prompt
from harness.context import ObservationTrimmer
from harness.steering import LoopDetector
from harness.guardrails import BudgetGuard, BudgetConfig
from harness.telemetry import TrajectoryRecorder, TrajectoryStep


@dataclass
class AgentResult:
    """Encapsulates the final outcome of an agent run."""
    success: bool
    final_text: str | None
    total_iterations: int
    total_prompt_tokens: int = 0
    total_response_tokens: int = 0
    estimated_cost_usd: float = 0.0
    trajectory_path: str | None = None
    error: str | None = None


class Agent:
    """
    Autonomous AI Software Engineering Agent with Harness Engineering.
    Coordinates LLM interactions, tool executions, context trimming, loop steering,
    budget enforcement, and trajectory telemetry.
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
        trimmer: ObservationTrimmer | None = None,
        loop_detector: LoopDetector | None = None,
        budget_guard: BudgetGuard | None = None,
        recorder: TrajectoryRecorder | None = None,
        enable_telemetry: bool = True,
    ) -> None:
        self.llm_client = llm_client or OpenRouterLLMClient()
        self.registry = registry or default_registry
        self.system_prompt = system_prompt
        self.working_directory = working_directory
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.verbose = verbose
        self.log = log_callback or (lambda msg: print(msg))
        self.trimmer = trimmer or ObservationTrimmer(max_chars=config.max_chars)
        self.loop_detector = loop_detector or LoopDetector()
        self.budget_guard = budget_guard
        self.recorder = recorder
        self.enable_telemetry = enable_telemetry

    def run(self, prompt: str) -> AgentResult:
        """Runs the agent loop for the given user prompt."""
        guard = self.budget_guard or BudgetGuard(BudgetConfig(max_iterations=self.max_iterations))
        guard.start()

        recorder = self.recorder or (TrajectoryRecorder() if self.enable_telemetry else None)
        model_name = getattr(self.llm_client, "model", "unknown")
        if recorder:
            recorder.initialize_session(
                prompt=prompt,
                model=model_name,
                working_directory=self.working_directory,
            )

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": prompt}
        ]

        total_prompt_tokens = 0
        total_response_tokens = 0

        for iteration in range(self.max_iterations):
            # Check budget constraints (iterations, tokens, execution time, cost)
            is_ok, budget_err = guard.check_budget(iteration=iteration + 1)
            if not is_ok:
                err_msg = f"Budget guardrail triggered: {budget_err}"
                if recorder:
                    recorder.finalize_session(
                        success=False,
                        final_text=None,
                        total_iterations=iteration,
                        total_prompt_tokens=total_prompt_tokens,
                        total_response_tokens=total_response_tokens,
                        estimated_cost_usd=guard.estimated_cost_usd,
                        error=err_msg,
                    )
                return AgentResult(
                    success=False,
                    final_text=None,
                    total_iterations=iteration,
                    total_prompt_tokens=total_prompt_tokens,
                    total_response_tokens=total_response_tokens,
                    estimated_cost_usd=guard.estimated_cost_usd,
                    trajectory_path=recorder.trajectory_path if recorder else None,
                    error=err_msg,
                )

            # Compact older observations if history becomes very large
            compacted_messages = self.trimmer.compact_messages(messages)

            try:
                response = self.llm_client.generate_content(
                    messages=compacted_messages,
                    tools=self.registry.to_tools(),
                    system_instruction=self.system_prompt,
                    temperature=self.temperature,
                )
            except Exception as e:
                err_msg = f"LLM generation failed: {e}"
                if recorder:
                    recorder.finalize_session(
                        success=False,
                        final_text=None,
                        total_iterations=iteration + 1,
                        total_prompt_tokens=total_prompt_tokens,
                        total_response_tokens=total_response_tokens,
                        estimated_cost_usd=guard.estimated_cost_usd,
                        error=err_msg,
                    )
                return AgentResult(
                    success=False,
                    final_text=None,
                    total_iterations=iteration + 1,
                    total_prompt_tokens=total_prompt_tokens,
                    total_response_tokens=total_response_tokens,
                    estimated_cost_usd=guard.estimated_cost_usd,
                    trajectory_path=recorder.trajectory_path if recorder else None,
                    error=err_msg,
                )

            total_prompt_tokens += response.prompt_tokens
            total_response_tokens += response.completion_tokens
            guard.record_usage(response.prompt_tokens, response.completion_tokens)

            if self.verbose:
                self.log(f"\n--- Iteration {iteration + 1} ---")
                self.log(f"User prompt: {prompt}")
                self.log(f"Prompt tokens: {response.prompt_tokens}")
                self.log(f"Response tokens: {response.completion_tokens}")

            step_tool_calls: list[dict[str, Any]] = []
            step_tool_results: list[dict[str, Any]] = []

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
                                    if tc.args is not None
                                    else "{}"
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

                    step_tool_calls.append({"id": tc.id, "name": fn_name, "args": fn_args})

                    if self.verbose:
                        self.log(f"Calling function: {fn_name}({tc.args})")
                    else:
                        self.log(f" - Calling function: {fn_name}")

                    raw_result = str(self.registry.execute(fn_name, **fn_args))

                    # Harness Enhancement: Enrich error messages with actionable guidance
                    enriched_result = (
                        self.loop_detector.enrich_error(fn_name, raw_result)
                        if raw_result.startswith("Error")
                        else raw_result
                    )

                    # Harness Enhancement: Check for repetitive tool cycles
                    intervention = self.loop_detector.record_and_check(
                        fn_name, fn_args, enriched_result
                    )

                    # Harness Enhancement: Smart head/tail observation trimming
                    trimmed_result = self.trimmer.trim(
                        enriched_result, label=f"Tool '{fn_name}'"
                    )

                    final_tool_content = trimmed_result
                    if intervention:
                        final_tool_content += f"\n\n{intervention}"
                        if self.verbose:
                            self.log(f" [Harness Steering Alert]: {intervention}")

                    if self.verbose:
                        self.log(f"-> {trimmed_result}")

                    step_tool_results.append({"name": fn_name, "result": final_tool_content})

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": fn_name,
                            "content": final_tool_content,
                        }
                    )

                if recorder:
                    import datetime
                    recorder.record_step(
                        TrajectoryStep(
                            iteration=iteration + 1,
                            timestamp=datetime.datetime.utcnow().isoformat(),
                            prompt_tokens=response.prompt_tokens,
                            completion_tokens=response.completion_tokens,
                            assistant_text=response.text,
                            tool_calls=step_tool_calls,
                            tool_results=step_tool_results,
                        )
                    )
            else:
                final_text = response.text or ""
                if recorder:
                    recorder.finalize_session(
                        success=True,
                        final_text=final_text,
                        total_iterations=iteration + 1,
                        total_prompt_tokens=total_prompt_tokens,
                        total_response_tokens=total_response_tokens,
                        estimated_cost_usd=guard.estimated_cost_usd,
                    )
                return AgentResult(
                    success=True,
                    final_text=final_text,
                    total_iterations=iteration + 1,
                    total_prompt_tokens=total_prompt_tokens,
                    total_response_tokens=total_response_tokens,
                    estimated_cost_usd=guard.estimated_cost_usd,
                    trajectory_path=recorder.trajectory_path if recorder else None,
                )

        limit_err = f"Agent reached the maximum iteration limit ({self.max_iterations}) without finishing."
        if recorder:
            recorder.finalize_session(
                success=False,
                final_text=None,
                total_iterations=self.max_iterations,
                total_prompt_tokens=total_prompt_tokens,
                total_response_tokens=total_response_tokens,
                estimated_cost_usd=guard.estimated_cost_usd,
                error=limit_err,
            )
        return AgentResult(
            success=False,
            final_text=None,
            total_iterations=self.max_iterations,
            total_prompt_tokens=total_prompt_tokens,
            total_response_tokens=total_response_tokens,
            estimated_cost_usd=guard.estimated_cost_usd,
            trajectory_path=recorder.trajectory_path if recorder else None,
            error=limit_err,
        )
