from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import OCREngine, OCRLine, OCRResult, sort_reading_order

if TYPE_CHECKING:
    from ..config import Settings
    from ..explain.llm_client import GeminiClient, LLMClient


def get_engine(name: str, device: str = "auto", *, gemini: GeminiClient | None = None) -> OCREngine:
    """`gemini` is a GeminiClient, needed only for the "gemini" engine."""
    if name == "gemini":
        from .gemini_engine import GeminiOCREngine

        if gemini is None:
            raise ValueError("the gemini OCR engine needs a GeminiClient")
        return GeminiOCREngine(gemini)
    if name == "paddle":
        from .paddle_engine import PaddleOCREngine
        from .routing import ScriptRoutingEngine

        return ScriptRoutingEngine(
            korean=PaddleOCREngine(device=device, lang="korean"),
            make_english=lambda: PaddleOCREngine(device=device, lang="en"),
        )
    raise ValueError(f"Unknown OCR engine: {name!r}")


def engine_from_settings(cfg: Settings, llm: LLMClient | Any) -> OCREngine:
    """The OCR engine the settings ask for. The Gemini engine shares the LLM's client when it can,
    so both draw on one request pace (the free tier quota is per project)."""
    if cfg.ocr_engine == "gemini":
        from ..explain.llm_client import GeminiClient

        client = llm if isinstance(llm, GeminiClient) else GeminiClient(
            cfg.llm_api_key, cfg.ocr_model or cfg.llm_model
        )
        return get_engine("gemini", gemini=client)
    return get_engine(cfg.ocr_engine, cfg.ocr_device)


__all__ = ["OCREngine", "OCRLine", "OCRResult", "engine_from_settings", "get_engine", "sort_reading_order"]
