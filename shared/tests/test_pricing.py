from __future__ import annotations

from shared.pricing import estimate_cost_usd, get_model_pricing
from shared.usage import cost_from_attributes, resolve_cost


def test_gpt4o_mini_pricing() -> None:
    rates = get_model_pricing("gpt-4o-mini")
    assert rates["input"] == 0.15
    assert rates["output"] == 0.60


def test_estimate_cost_from_tokens() -> None:
    cost = estimate_cost_usd("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=0)
    assert cost == 0.15


def test_resolve_cost_estimates_when_missing_explicit_cost() -> None:
    cost = resolve_cost(
        {
            "model": "gpt-4o-mini",
            "prompt_tokens": 128,
            "completion_tokens": 24,
        }
    )
    assert cost is not None
    assert cost > 0


def test_cost_from_attributes() -> None:
    cost = cost_from_attributes(
        {
            "agentops.model": "gpt-4o-mini",
            "agentops.prompt_tokens": 312,
            "agentops.completion_tokens": 89,
        }
    )
    assert cost is not None
    assert round(cost, 6) == 0.0001
