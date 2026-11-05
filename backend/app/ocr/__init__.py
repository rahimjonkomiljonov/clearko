from .base import OCREngine, OCRLine, OCRResult, sort_reading_order


def get_engine(name: str) -> OCREngine:
    if name == "paddle":
        from .paddle_engine import PaddleOCREngine

        return PaddleOCREngine()
    raise ValueError(f"Unknown OCR engine: {name!r}")


__all__ = ["OCREngine", "OCRLine", "OCRResult", "get_engine", "sort_reading_order"]
