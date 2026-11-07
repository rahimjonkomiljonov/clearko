"""Check the Gemini setup: which models the key can use, and one tiny test call.

    cd backend && .venv/Scripts/python ../eval/tools/check_gemini.py [model-id]

Reads LLM_API_KEY from .env (via the app settings). The key is never printed. The test call sends
only the word "ping", no document text.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from google import genai

from app.config import get_settings
from app.explain.llm_client import GeminiClient, LLMError


def main() -> int:
    cfg = get_settings()
    if not cfg.llm_api_key:
        print("LLM_API_KEY is empty. Put the key on the LLM_API_KEY= line of ClearKo/.env")
        return 2
    client = genai.Client(api_key=cfg.llm_api_key)
    try:
        models = [m for m in client.models.list()
                  if "generateContent" in (m.supported_actions or [])]
    except Exception as e:  # noqa: BLE001  never print request details, only the error type
        print(f"Could not list models ({type(e).__name__}): is the key valid?")
        return 3
    names = sorted(m.name.removeprefix("models/") for m in models)
    flash = [n for n in names if "flash" in n and "image" not in n and "tts" not in n]
    print(f"{len(names)} text models usable with this key. Flash models:")
    for n in flash:
        print("  ", n)
    wanted = sys.argv[1] if len(sys.argv) > 1 else cfg.llm_model
    if wanted not in names:
        print(f"\nConfigured model {wanted!r} is not available to this key.")
        return 4
    try:
        out = GeminiClient(cfg.llm_api_key, wanted).generate(
            "Reply with JSON only.", [("user", 'Return {"reply": "pong"} for the word: ping')]
        )
    except LLMError as e:
        print(f"\nTest call failed: {e}")
        return 5
    print(f"\nTest call to {wanted!r} worked: {out.strip()[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
