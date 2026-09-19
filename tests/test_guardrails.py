import time
from harness.guardrails import BudgetGuard, BudgetConfig


def test_budget_guard_iterations():
    guard = BudgetGuard(BudgetConfig(max_iterations=5))
    guard.start()

    ok, reason = guard.check_budget(iteration=3)
    assert ok is True
    assert reason is None

    ok, reason = guard.check_budget(iteration=6)
    assert ok is False
    assert "Maximum iteration limit exceeded" in reason


def test_budget_guard_tokens():
    guard = BudgetGuard(BudgetConfig(max_total_tokens=100))
    guard.start()
    guard.record_usage(prompt_tokens=50, completion_tokens=60)

    ok, reason = guard.check_budget(iteration=1)
    assert ok is False
    assert "Maximum token budget exceeded" in reason


def test_budget_guard_time_limit():
    guard = BudgetGuard(BudgetConfig(max_time_seconds=0.1))
    guard.start()
    time.sleep(0.15)

    ok, reason = guard.check_budget(iteration=1)
    assert ok is False
    assert "Execution time limit exceeded" in reason


def test_budget_guard_cost_estimation():
    guard = BudgetGuard(
        BudgetConfig(
            max_cost_usd=0.01,
            prompt_token_cost_per_million=10.0,
            completion_token_cost_per_million=20.0,
        )
    )
    guard.start()
    guard.record_usage(prompt_tokens=1_000, completion_tokens=500)
    # Cost = 1000 * 10 / 1M + 500 * 20 / 1M = 0.01 + 0.01 = 0.02
    assert guard.estimated_cost_usd == 0.02

    ok, reason = guard.check_budget(iteration=1)
    assert ok is False
    assert "cost ceiling exceeded" in reason
