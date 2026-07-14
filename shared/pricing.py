from __future__ import annotations

# USD per 1M tokens (input / output). Approximate public list prices for local estimates.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}

DEFAULT_PRICING = MODEL_PRICING["gpt-4o-mini"]


def normalize_model_name(model: str | None) -> str:
    if not model:
        return ""
    normalized = model.strip().lower()
    for prefix in ("openai:", "azure:", "anthropic:", "google:", "models/"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    return normalized


def get_model_pricing(model: str | None) -> dict[str, float]:
    normalized = normalize_model_name(model)
    if not normalized:
        return DEFAULT_PRICING

    if normalized in MODEL_PRICING:
        return MODEL_PRICING[normalized]

    for key, pricing in MODEL_PRICING.items():
        if key in normalized or normalized in key:
            return pricing

    return DEFAULT_PRICING


def estimate_cost_usd(
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    rates = get_model_pricing(model)
    return (prompt_tokens * rates["input"] + completion_tokens * rates["output"]) / 1_000_000
