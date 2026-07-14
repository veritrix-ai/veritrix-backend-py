from __future__ import annotations

from typing import Any

from shared.pricing import estimate_cost_usd

PROMPT_TOKEN_KEYS = (
    "agentops.prompt_tokens",
    "gen_ai.usage.input_tokens",
    "gen_ai.usage.prompt_tokens",
    "llm.usage.prompt_tokens",
)

COMPLETION_TOKEN_KEYS = (
    "agentops.completion_tokens",
    "gen_ai.usage.output_tokens",
    "gen_ai.usage.completion_tokens",
    "llm.usage.completion_tokens",
)

TOTAL_TOKEN_KEYS = (
    "agentops.total_tokens",
    "gen_ai.usage.total_tokens",
    "llm.usage.total_tokens",
)

MODEL_KEYS = (
    "agentops.model",
    "gen_ai.request.model",
    "gen_ai.response.model",
    "llm.model_name",
)

COST_KEYS = ("agentops.cost_usd", "gen_ai.usage.cost")


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_int(attributes: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        parsed = _coerce_int(attributes.get(key))
        if parsed is not None:
            return parsed
    return None


def _first_str(attributes: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = attributes.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_float(attributes: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        parsed = _coerce_float(attributes.get(key))
        if parsed is not None:
            return parsed
    return None


def parse_usage(attributes: dict[str, Any]) -> dict[str, Any]:
    prompt_tokens = _first_int(attributes, PROMPT_TOKEN_KEYS)
    completion_tokens = _first_int(attributes, COMPLETION_TOKEN_KEYS)
    total_tokens = _first_int(attributes, TOTAL_TOKEN_KEYS)
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "model": _first_str(attributes, MODEL_KEYS),
        "cost_usd": _first_float(attributes, COST_KEYS),
    }


def resolve_cost(usage: dict[str, Any]) -> float | None:
    explicit = usage.get("cost_usd")
    if explicit is not None and explicit > 0:
        return float(explicit)

    prompt_tokens = usage.get("prompt_tokens") or 0
    completion_tokens = usage.get("completion_tokens") or 0
    if prompt_tokens == 0 and completion_tokens == 0:
        return float(explicit) if explicit is not None else None

    return estimate_cost_usd(usage.get("model"), int(prompt_tokens), int(completion_tokens))


def cost_from_attributes(attributes: dict[str, Any]) -> float | None:
    return resolve_cost(parse_usage(attributes))


def sum_total_tokens(spans: list[Any]) -> int:
    total = 0
    for span in spans:
        if getattr(span, "total_tokens", None) is not None:
            total += int(span.total_tokens)
            continue
        usage = parse_usage(getattr(span, "attributes", {}) or {})
        token_count = usage.get("total_tokens")
        if token_count is not None:
            total += int(token_count)
    return total


def sum_cost_usd(spans: list[Any]) -> float:
    total = 0.0
    for span in spans:
        if getattr(span, "cost_usd", None) is not None:
            total += float(span.cost_usd)
            continue
        usage = parse_usage(getattr(span, "attributes", {}) or {})
        cost = resolve_cost(usage)
        if cost is not None:
            total += cost
    return total
