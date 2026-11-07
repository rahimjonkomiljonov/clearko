from __future__ import annotations

import json
import threading
import time
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
    """Google Gemini API. The document text LEAVES the machine; on the free tier Google may use it
    to improve its products, so use it for sample documents only (see README, "Deploy")."""

    RETRY_CODES = (429, 500, 502, 503, 504)

    def __init__(
        self,
        api_key: str,
        model: str,
        min_interval_s: float = 4.2,  # free tier: 15 requests per minute
        retries: int = 3,
        sleep=time.sleep,
        clock=time.monotonic,
    ) -> None:
        if not api_key:
            raise LLMError("LLM_API_KEY is not set. Add it to .env (see .env.example).")
        from google import genai  # imported lazily

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._min_interval = min_interval_s
        self._retries = retries
        self._sleep = sleep
        self._clock = clock
        self._last_call = -1e9
        self._lock = threading.Lock()

    def _pace(self) -> None:
        """Keep a minimum gap between requests so the per-minute quota is not hit."""
        with self._lock:
            wait = self._last_call + self._min_interval - self._clock()
            if wait > 0:
                self._sleep(wait)
            self._last_call = self._clock()

    def generate(
        self, system: str, messages: list[tuple[str, str]], json_schema: dict | None = None
    ) -> str:
        from google.genai import types

        contents = [types.Content(role=r, parts=[types.Part(text=t)]) for r, t in messages]
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=json_schema,  # None = any JSON
            temperature=0.2,
            seed=7,
            max_output_tokens=8192,
        )
        return self._call(contents, config)

    def transcribe(self, image_jpeg: bytes, instruction: str) -> str:
        """Plain-text answer about one image (used for OCR). The image LEAVES the machine."""
        from google.genai import types

        contents = [types.Content(role="user", parts=[
            types.Part.from_bytes(data=image_jpeg, mime_type="image/jpeg"),
            types.Part(text=instruction),
        ])]
        config = types.GenerateContentConfig(temperature=0.0, seed=7, max_output_tokens=8192)
        return self._call(contents, config)

    def _call(self, contents, config) -> str:
        resp = None
        for attempt in range(self._retries + 1):
            self._pace()
            try:
                resp = self._client.models.generate_content(
                    model=self._model, contents=contents, config=config
                )
                break
            except Exception as e:  # noqa: BLE001  SDK raises many types; never include request content
                code = getattr(e, "code", None)
                if code in self.RETRY_CODES and attempt < self._retries:
                    self._sleep(15.0 * (attempt + 1))  # quota resets per minute
                    continue
                hint = " (rate limit: wait a minute)" if code == 429 else ""
                raise LLMError(f"Gemini request failed: {type(e).__name__} {code or ''}{hint}") from None
        if resp is None or not resp.text:
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
