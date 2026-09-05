"""
Selects an LLM provider based on config, same pattern as
app/execution/gateway_factory.py. Returns None if no provider is
configured or initialization fails — callers must handle None as
"use the template fallback", never as an error.
"""

from app.config import settings


def get_llm_provider():
    provider_name = (settings.LLM_PROVIDER or "").lower()

    try:
        if provider_name == "anthropic" and settings.ANTHROPIC_API_KEY:
            from app.receivables.anthropic_provider import AnthropicProvider

            return AnthropicProvider(settings.ANTHROPIC_API_KEY)

        if provider_name == "gemini" and settings.GEMINI_API_KEY:
            from app.receivables.gemini_provider import GeminiProvider

            return GeminiProvider(settings.GEMINI_API_KEY)
    except Exception:
        return None

    return None
