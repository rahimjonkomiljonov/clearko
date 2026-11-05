from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """The LLM call failed (network, quota, safety block). Message never contains document text."""


class LLMClient(ABC):
    @abstractmethod
    def generate(self, system: str, messages: list[tuple[str, str]]) -> str:
        """messages: list of (role, text) with role 'user' or 'model'. Returns the raw reply."""


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMError("LLM_API_KEY is not set. Add it to .env (see .env.example).")
        from google import genai  # imported lazily

        self._genai = genai
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, system: str, messages: list[tuple[str, str]]) -> str:
        from google.genai import types

        contents = [types.Content(role=r, parts=[types.Part(text=t)]) for r, t in messages]
        try:
            resp = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
        except Exception as e:  # noqa: BLE001  SDK raises many types; never include request content
            raise LLMError(f"Gemini request failed: {type(e).__name__}") from None
        if not resp.text:
            raise LLMError("Gemini returned an empty response (possibly blocked)")
        return resp.text


def get_llm_client(provider: str, api_key: str, model: str) -> LLMClient:
    if provider == "gemini":
        return GeminiClient(api_key, model)
    raise ValueError(f"Unknown LLM provider: {provider!r}")
