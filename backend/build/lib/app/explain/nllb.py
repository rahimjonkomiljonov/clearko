"""Offline translation with Meta's NLLB-200 (needs the optional 'uz' extra: torch + transformers).

LICENSE: the NLLB-200 weights are CC-BY-NC 4.0, i.e. NON-COMMERCIAL use only.

Why it exists: the local chat models (qwen2.5:7b, gemma3:4b) cannot write Uzbek. NLLB is a
dedicated translation model that supports Uzbek. It translates one sentence at a time (long
inputs lose sentences), then the sentences are joined again.

The model runs in a separate worker process (see nllb_worker.py) because torch and PaddleOCR
cannot be loaded into the same Windows process.
"""

from __future__ import annotations

import atexit
import importlib.metadata
import json
import re
import subprocess
import sys

from .llm_client import LLMError

DEFAULT_MODEL = "facebook/nllb-200-distilled-1.3B"
LANG_CODES = {"uz": "uzn_Latn", "ru": "rus_Cyrl", "en": "eng_Latn"}

# Split after . ! ? when a new sentence (capital letter, digit, bracket or quote) follows.
# "1.5", "e.g. x" and "5,000" are not split because no capital letter / space pattern matches.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'])")


class NLLBUnavailable(RuntimeError):
    """torch / transformers are not installed."""


def nllb_available() -> bool:
    """Checked from package metadata, without importing torch (that would clash with PaddleOCR)."""
    try:
        for dist in ("torch", "transformers", "sentencepiece"):
            importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_END.split(text.strip())]
    return [p for p in parts if p]


class NLLBTranslator:
    """Callable StringTranslator. The worker starts on first use and stays alive."""

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str = "auto"):
        self.model_name = model_name
        self.device = device
        self._proc: subprocess.Popen[str] | None = None

    def __call__(self, lang: str, strings: list[str]) -> list[str] | None:
        if lang not in LANG_CODES:
            return None
        pieces: list[list[str]] = [split_sentences(s) for s in strings]
        flat = [p for sentences in pieces for p in sentences]
        if not flat:
            return list(strings)
        done = self._run(LANG_CODES[lang], flat)
        out: list[str] = []
        pos = 0
        for sentences in pieces:
            out.append(" ".join(done[pos : pos + len(sentences)]))
            pos += len(sentences)
        return out

    # ----- worker process -----
    def _start(self) -> subprocess.Popen[str]:
        if self._proc is None or self._proc.poll() is not None:
            if not nllb_available():
                raise NLLBUnavailable("Install the 'uz' extra: pip install -e \".[uz]\"")
            self._proc = subprocess.Popen(
                [sys.executable, "-m", "app.explain.nllb_worker", self.model_name, self.device],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8",
            )
            atexit.register(self.close)
        return self._proc

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.kill()
        self._proc = None

    def _run(self, target_code: str, sentences: list[str]) -> list[str]:
        proc = self._start()
        assert proc.stdin is not None and proc.stdout is not None
        try:
            proc.stdin.write(json.dumps({"code": target_code, "sentences": sentences}) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
        except OSError as e:
            self.close()
            raise LLMError(f"Translation worker failed: {type(e).__name__}") from None
        if not line:
            self.close()
            raise LLMError("Translation worker stopped unexpectedly")
        reply = json.loads(line)
        if "error" in reply or len(reply.get("sentences", [])) != len(sentences):
            raise LLMError(f"Translation worker failed: {reply.get('error', 'wrong length')}")
        return list(reply["sentences"])
