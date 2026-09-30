"""Claude model catalog: model IDs, context windows, and pricing.

Single source of truth for the Anthropic models Teotl knows about. Used by
AnthropicProvider (context window), guardrails cost estimation, and the
onboarding wizard (defaults).

Pricing is the Anthropic first-party API list price in USD per million
tokens, as of September 2026. Unknown models still work; they just fall
back to a conservative context window and no cost estimate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaudeModel:
    context_window: int
    input_per_mtok: float
    output_per_mtok: float


_1M = 1_000_000
_200K = 200_000

CLAUDE_MODELS: dict[str, ClaudeModel] = {
    # Current models
    "claude-fable-5-1": ClaudeModel(_1M, 10.00, 50.00),
    "claude-fable-5": ClaudeModel(_1M, 10.00, 50.00),
    "claude-opus-5-5": ClaudeModel(_1M, 4.00, 20.00),
    "claude-opus-5": ClaudeModel(_1M, 5.00, 25.00),
    "claude-opus-4-8": ClaudeModel(_1M, 5.00, 25.00),
    "claude-opus-4-7": ClaudeModel(_1M, 5.00, 25.00),
    "claude-opus-4-6": ClaudeModel(_1M, 5.00, 25.00),
    "claude-sonnet-5-5": ClaudeModel(_1M, 2.00, 10.00),
    "claude-sonnet-5": ClaudeModel(_1M, 2.00, 10.00),
    "claude-sonnet-4-6": ClaudeModel(_1M, 3.00, 15.00),
    "claude-haiku-4-5": ClaudeModel(_200K, 1.00, 5.00),
    "claude-haiku-4-5-20251001": ClaudeModel(_200K, 1.00, 5.00),
    # Legacy models (still served)
    "claude-opus-4-5": ClaudeModel(_200K, 5.00, 25.00),
    "claude-opus-4-5-20251101": ClaudeModel(_200K, 5.00, 25.00),
    "claude-sonnet-4-5": ClaudeModel(_200K, 3.00, 15.00),
    "claude-sonnet-4-5-20250929": ClaudeModel(_200K, 3.00, 15.00),
    # Deprecated (retirement announced) - migrate off these
    "claude-opus-4-0": ClaudeModel(_200K, 15.00, 75.00),
    "claude-opus-4-20250514": ClaudeModel(_200K, 15.00, 75.00),
    "claude-sonnet-4-0": ClaudeModel(_200K, 3.00, 15.00),
    "claude-sonnet-4-20250514": ClaudeModel(_200K, 3.00, 15.00),
}

# Defaults: a capable planner/general model and a fast, cheap worker model.
DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_PLANNER_MODEL = "claude-sonnet-5-5"
DEFAULT_WORKER_MODEL = "claude-haiku-4-5"

# Context window assumed for Claude models not in the catalog.
DEFAULT_CONTEXT_WINDOW = _200K
