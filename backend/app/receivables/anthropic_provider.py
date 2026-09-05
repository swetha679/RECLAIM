from app.receivables.llm_provider import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()
        if not text:
            raise ValueError("empty response from Anthropic")
        return text
