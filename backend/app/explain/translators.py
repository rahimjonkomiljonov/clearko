"""Pick the translator for a language from the settings."""

from __future__ import annotations

from collections.abc import Callable

from ..config import Settings
from .llm_client import LLMClient, get_llm_client
from .nllb import NLLBTranslator, nllb_available
from .translate import StringTranslator

_nllb_cache: dict[tuple[str, str], NLLBTranslator] = {}  # keep the model loaded between requests


def get_translator(
    lang: str, settings: Settings, log: Callable[[str], None] | None = None
) -> LLMClient | StringTranslator | None:
    """None means: translate with the main chat model."""
    if lang == "en":
        return None
    if settings.llm_provider != "ollama":
        # a cloud model writes Russian and Uzbek itself; the local translators (and their model
        # names, which mean nothing to a cloud API) do not apply
        return None
    if lang == "uz" and settings.uz_translator == "nllb":
        if nllb_available():
            key = (settings.nllb_model, settings.nllb_device)
            if key not in _nllb_cache:
                _nllb_cache[key] = NLLBTranslator(*key)
            return _nllb_cache[key]
        if log:
            log("NLLB is not installed (pip install -e \".[uz]\"): Uzbek will be poor quality")
    if settings.llm_translate_model:
        return get_llm_client(
            settings.llm_provider, settings.llm_api_key,
            settings.llm_translate_model, settings.llm_base_url,
        )
    return None
