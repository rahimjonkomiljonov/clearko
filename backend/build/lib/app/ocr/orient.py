from __future__ import annotations

import cv2
import numpy as np

from .base import OCREngine, OCRResult

_ROTATIONS = (
    cv2.ROTATE_90_CLOCKWISE,
    cv2.ROTATE_180,
    cv2.ROTATE_90_COUNTERCLOCKWISE,
)


def _score(result: OCRResult) -> float:
    """Confidence-weighted amount of text. Wrong orientations give few, low-confidence lines."""
    return sum(line.confidence * len(line.text) for line in result.lines)


def recognize_upright(
    engine: OCREngine, image: np.ndarray, min_confidence: float = 0.85
) -> tuple[OCRResult, int]:
    """OCR the image as-is; if confidence is low, also try 90/180/270 degree rotations.

    Returns (best result, clockwise degrees applied to the input: 0, 90, 180 or 270).
    """
    best = engine.recognize(image)
    best_deg = 0
    if best.lines and best.mean_confidence >= min_confidence:
        return best, 0
    for code, deg in zip(_ROTATIONS, (90, 180, 270)):
        candidate = engine.recognize(cv2.rotate(image, code))
        if _score(candidate) > _score(best) * 1.2:  # require a clear win to avoid flip-flopping
            best, best_deg = candidate, deg
    return best, best_deg
