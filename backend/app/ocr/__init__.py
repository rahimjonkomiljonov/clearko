from .base import OCREngine, OCRLine, OCRResult, sort_reading_order


def get_engine(name: str, device: str = "auto") -> OCREngine:
    if name == "paddle":
        from .paddle_engine import PaddleOCREngine

        return PaddleOCREngine(device=device)
    raise ValueError(f"Unknown OCR engine: {name!r}")


__all__ = ["OCREngine", "OCRLine", "OCRResult", "get_engine", "sort_reading_order"]
