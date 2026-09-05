from app.receivables.llm_provider import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel("gemini-1.5-flash")

    def generate(self, prompt: str) -> str:
        response = self._model.generate_content(prompt)
        text = (response.text or "").strip()
        if not text:
            raise ValueError("empty response from Gemini")
        return text
