import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class BudgetConfig:
    max_iterations: int = 20
    max_total_tokens: int = 100_000
    max_time_seconds: float = 300.0
    max_cost_usd: float = 2.0
    # Default rates based on typical OpenRouter fast model pricing ($/1M tokens)
    prompt_token_cost_per_million: float = 0.15
    completion_token_cost_per_million: float = 0.60


class BudgetGuard:
    """
    Harness Guardrail that tracks execution budgets:
    iterations, tokens, wall-clock time, and estimated cost.
    Guarantees that an agent does not run indefinitely or exceed financial thresholds.
    """

    def __init__(self, config: Optional[BudgetConfig] = None) -> None:
        self.config = config or BudgetConfig()
        self.start_time: float = time.time()
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0

    def start(self) -> None:
        """Resets the timer for a new agent run."""
        self.start_time = time.time()
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def record_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def estimated_cost_usd(self) -> float:
        prompt_cost = (self.total_prompt_tokens / 1_000_000.0) * self.config.prompt_token_cost_per_million
        comp_cost = (self.total_completion_tokens / 1_000_000.0) * self.config.completion_token_cost_per_million
        return round(prompt_cost + comp_cost, 6)

    def check_budget(self, iteration: int) -> tuple[bool, str | None]:
        """
        Checks whether any budget constraint has been violated.
        Returns (is_ok, violation_reason).
        """
        if iteration > self.config.max_iterations:
            return False, f"Maximum iteration limit exceeded ({iteration} > {self.config.max_iterations})"

        if self.total_tokens > self.config.max_total_tokens:
            return False, f"Maximum token budget exceeded ({self.total_tokens} > {self.config.max_total_tokens})"

        elapsed = self.elapsed_seconds
        if elapsed > self.config.max_time_seconds:
            return False, f"Execution time limit exceeded ({elapsed:.1f}s > {self.config.max_time_seconds}s)"

        cost = self.estimated_cost_usd
        if cost > self.config.max_cost_usd:
            return False, f"Estimated cost ceiling exceeded (${cost:.4f} > ${self.config.max_cost_usd:.4f})"

        return True, None
