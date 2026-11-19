"""Approximate list prices in USD per million tokens, used only for cost estimates in reports.

Check https://platform.claude.com/docs/en/about-claude/pricing before relying on these.
Cache reads are billed at about 10% of input and 5-minute cache writes at 1.25x input.
"""

from __future__ import annotations

from .agents.base import Usage

PRICES = {  # model id prefix -> (input, output)
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}


def estimate(model: str | None, u: Usage) -> float | None:
    if not model:
        return None
    price = next((p for k, p in PRICES.items() if model.startswith(k)), None)
    if price is None:
        return None
    inp, out = price
    return (u.input_tokens * inp + u.cache_read_tokens * inp * 0.1
            + u.cache_write_tokens * inp * 1.25 + u.output_tokens * out) / 1e6
