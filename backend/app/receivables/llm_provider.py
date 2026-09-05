"""
General contract any LLM provider must implement, for message generation
only (see message_generator.py for the scope boundary — never used for
retry/escalate/dispute decisions).

Same pattern as app/execution/gateway_interface.py: pipelines depend on
this interface, not on any specific provider. Anthropic and Gemini are
both implemented today; switching is a config change (LLM_PROVIDER in
.env), not a code change.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Returns generated text, or raises on any failure (auth, network,
        rate limit, empty response) — callers must catch and fall back."""
        raise NotImplementedError
