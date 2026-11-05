from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """The LLM call failed (network, quota, safety block). Message never contains document text."""


class LLMClient(ABC):
    @abstractmethod
    def generate(
        self, system: str, messages: list[tuple[str, str]], json_schema: dict | None = None
    ) -> str:
        """messages: list of (role, text), role 'user' or 'model'. Returns the raw reply.

        json_schema, when given, asks the backend to constrain its output to that schema.
        """


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMError("LLM_API_KEY is not set. Add it to .env (see .env.example).")
        from google import genai  # imported lazily

        self._genai = genai
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(
        self, system: str, messages: list[tuple[str, str]], json_schema: dict | None = None
    ) -> str:
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


class OllamaClient(LLMClient):
    """Local model through Ollama's HTTP API. Nothing leaves the machine."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        num_ctx: int = 12288,
        timeout_s: float = 300.0,
        max_tokens: int = 4096,  # hard cap so a looping model cannot run until the timeout
        force_json: bool = True,  # False = free text (only the evaluation baseline needs that)
    ) -> None:
        self._force_json = force_json
        self._model = model
        self._max_tokens = max_tokens
        self._url = base_url.rstrip("/") + "/api/chat"
        self._num_ctx = num_ctx
        self._timeout = timeout_s

    def generate(
        self, system: str, messages: list[tuple[str, str]], json_schema: dict | None = None
    ) -> str:
        chat = [{"role": "system", "content": system}] + [
            {"role": "assistant" if r == "model" else "user", "content": t} for r, t in messages
        ]
        body = {
            "model": self._model,
            "messages": chat,
            "stream": False,
            **({"format": json_schema or "json"} if (json_schema or self._force_json) else {}),
            "options": {
                "temperature": 0.2,
                "seed": 7,  # same input -> same output, so runs can be compared
                "num_ctx": self._num_ctx,
                "num_predict": self._max_tokens,
            },
        }
        req = urllib.request.Request(
            self._url, json.dumps(body).encode("utf-8"), {"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            hint = " (model not pulled? run: ollama pull " + self._model + ")" if e.code == 404 else ""
            raise LLMError(f"Ollama returned HTTP {e.code}{hint}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            reason = getattr(e, "reason", e)  # connection details only, never request content
            raise LLMError(
                f"Cannot reach Ollama at {self._url} ({type(reason).__name__}: {reason}). Is it running?"
            ) from None
        except json.JSONDecodeError:
            raise LLMError("Ollama returned an unreadable response") from None
        text = (data.get("message") or {}).get("content", "")
        if not text.strip():
            raise LLMError("Ollama returned an empty response")
        return text


def get_llm_client(
    provider: str, api_key: str = "", model: str = "", base_url: str = ""
) -> LLMClient:
    if provider == "ollama":
        return OllamaClient(model, base_url or "http://localhost:11434")
    if provider == "gemini":
        return GeminiClient(api_key, model)
    raise ValueError(f"Unknown LLM provider: {provider!r}")
