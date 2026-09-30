"""Model catalog: model IDs, context windows, and pricing per provider.

Single source of truth for the models Teotl knows about. Used by the
providers (context window), guardrails cost estimation, and the onboarding
wizard (defaults).

Prices are first-party API list prices in USD per million tokens (standard
tier, shortest prompt band), as of September 2026. Unknown models still work;
they just fall back to a conservative context window and no cost estimate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    context_window: int
    input_per_mtok: float
    output_per_mtok: float


ClaudeModel = ModelInfo  # earlier name


_1M = 1_000_000
_200K = 200_000

CLAUDE_MODELS: dict[str, ClaudeModel] = {
    # Current models
    "claude-fable-5-1": ModelInfo(_1M, 10.00, 50.00),
    "claude-fable-5": ModelInfo(_1M, 10.00, 50.00),
    "claude-opus-5-5": ModelInfo(_1M, 4.00, 20.00),
    "claude-opus-5": ModelInfo(_1M, 5.00, 25.00),
    "claude-opus-4-8": ModelInfo(_1M, 5.00, 25.00),
    "claude-opus-4-7": ModelInfo(_1M, 5.00, 25.00),
    "claude-opus-4-6": ModelInfo(_1M, 5.00, 25.00),
    "claude-sonnet-5-5": ModelInfo(_1M, 2.00, 10.00),
    "claude-sonnet-5": ModelInfo(_1M, 2.00, 10.00),
    "claude-sonnet-4-6": ModelInfo(_1M, 3.00, 15.00),
    "claude-haiku-4-5": ModelInfo(_200K, 1.00, 5.00),
    "claude-haiku-4-5-20251001": ModelInfo(_200K, 1.00, 5.00),
    # Legacy models (still served)
    "claude-opus-4-5": ModelInfo(_200K, 5.00, 25.00),
    "claude-opus-4-5-20251101": ModelInfo(_200K, 5.00, 25.00),
    "claude-sonnet-4-5": ModelInfo(_200K, 3.00, 15.00),
    "claude-sonnet-4-5-20250929": ModelInfo(_200K, 3.00, 15.00),
    # Deprecated (retirement announced) - migrate off these
    "claude-opus-4-0": ModelInfo(_200K, 15.00, 75.00),
    "claude-opus-4-20250514": ModelInfo(_200K, 15.00, 75.00),
    "claude-sonnet-4-0": ModelInfo(_200K, 3.00, 15.00),
    "claude-sonnet-4-20250514": ModelInfo(_200K, 3.00, 15.00),
}

# OpenAI (developers.openai.com/api/docs/pricing and /models, September 2026).
# Prompts over 272K input tokens cost more on the gpt-5.4+ models.
_1_05M = 1_050_000
OPENAI_MODELS: dict[str, ModelInfo] = {
    # GPT-6 family: tool calling needs the Responses API (see OPENAI_CHAT_TOOLS_UNSUPPORTED)
    "gpt-6-astra": ModelInfo(_1_05M, 10.00, 50.00),
    "gpt-6.1-sol": ModelInfo(_1_05M, 2.00, 10.00),
    "gpt-6-sol": ModelInfo(_1_05M, 2.00, 10.00),
    "gpt-6-luna": ModelInfo(_1_05M, 0.10, 0.50),
    # GPT-5.6 family: tool calling supported in Chat Completions
    "gpt-5.6-sol": ModelInfo(_1_05M, 4.00, 20.00),
    "gpt-5.6-terra": ModelInfo(_1_05M, 2.00, 12.00),
    "gpt-5.6-luna": ModelInfo(_1_05M, 0.20, 1.20),
    "gpt-5.5": ModelInfo(_1_05M, 5.00, 30.00),
    "gpt-5.5-pro": ModelInfo(_1_05M, 30.00, 180.00),
    "gpt-5.4": ModelInfo(_1_05M, 2.50, 15.00),
    "gpt-5.4-pro": ModelInfo(_1_05M, 30.00, 180.00),
    "gpt-5.4-mini": ModelInfo(400_000, 0.75, 4.50),
    "gpt-5.4-nano": ModelInfo(400_000, 0.20, 1.25),
    "gpt-5": ModelInfo(400_000, 1.25, 10.00),
    "gpt-5-mini": ModelInfo(400_000, 0.25, 2.00),
    "gpt-5-nano": ModelInfo(400_000, 0.05, 0.40),
    "gpt-4.1": ModelInfo(1_047_576, 2.00, 8.00),
    "gpt-4.1-mini": ModelInfo(1_047_576, 0.40, 1.60),
    "gpt-4.1-nano": ModelInfo(1_047_576, 0.10, 0.40),
    "gpt-4o": ModelInfo(128_000, 2.50, 10.00),
    "gpt-4o-mini": ModelInfo(128_000, 0.15, 0.60),
    "o3": ModelInfo(_200K, 2.00, 8.00),
    "o3-pro": ModelInfo(_200K, 20.00, 80.00),
    "o4-mini": ModelInfo(_200K, 1.10, 4.40),
}

# Models whose Chat Completions endpoint doesn't support tool calling (or only in a
# restricted mode). OpenAIProvider uses Chat Completions, so it warns for these.
OPENAI_CHAT_TOOLS_UNSUPPORTED = ("gpt-6",)

# Google Gemini (ai.google.dev/gemini-api/docs/pricing and /models, September 2026).
# gemini-3.6/3.7/3.8-flash are $0.75/$3.75 through 2026-12-31, then $1.50/$7.50.
# The 2.5 models are limited to projects that already used them; new projects
# should use 3.8 Flash or 3.5 Flash-Lite.
_1M_GEMINI = 1_048_576
GEMINI_MODELS: dict[str, ModelInfo] = {
    "gemini-3.8-flash": ModelInfo(_1M_GEMINI, 0.75, 3.75),
    "gemini-3.7-flash": ModelInfo(_1M_GEMINI, 0.75, 3.75),
    "gemini-3.6-flash": ModelInfo(_1M_GEMINI, 0.75, 3.75),
    "gemini-3.5-flash": ModelInfo(_1M_GEMINI, 1.50, 9.00),
    "gemini-3.5-flash-lite": ModelInfo(_1M_GEMINI, 0.30, 2.50),
    "gemini-3.1-flash-lite": ModelInfo(_1M_GEMINI, 0.25, 1.50),
    "gemini-3.1-pro-preview": ModelInfo(_1M_GEMINI, 2.00, 12.00),
    "gemini-3-flash-preview": ModelInfo(_1M_GEMINI, 0.50, 3.00),
    "gemini-2.5-pro": ModelInfo(_1M_GEMINI, 1.25, 10.00),
    "gemini-2.5-flash": ModelInfo(_1M_GEMINI, 0.30, 2.50),
    "gemini-2.5-flash-lite": ModelInfo(_1M_GEMINI, 0.10, 0.40),
}

# Defaults: a capable planner/general model and a fast, cheap worker model.
DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_PLANNER_MODEL = "claude-sonnet-5-5"
DEFAULT_WORKER_MODEL = "claude-haiku-4-5"

DEFAULT_OPENAI_MODEL = "gpt-5.6-terra"
DEFAULT_OPENAI_CAPABLE_MODEL = "gpt-5.6-sol"
DEFAULT_OPENAI_WORKER_MODEL = "gpt-5.6-luna"

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_GEMINI_WORKER_MODEL = "gemini-3.5-flash-lite"

def provider_for(model: str) -> str | None:
    """Pricing provider key ("anthropic", "openai", "google") for a cataloged model."""
    for provider, catalog in (
        ("anthropic", CLAUDE_MODELS),
        ("openai", OPENAI_MODELS),
        ("google", GEMINI_MODELS),
    ):
        if model in catalog:
            return provider
    return None


# Context window assumed for models not in the catalogs.
DEFAULT_CONTEXT_WINDOW = _200K
