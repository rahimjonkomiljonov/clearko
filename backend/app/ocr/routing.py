from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .base import OCREngine, OCRResult


def hangul_ratio(text: str) -> float:
    """Share of Hangul syllables among all letters (digits and punctuation ignored)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum("\uac00" <= c <= "\ud7a3" for c in letters) / len(letters)


class ScriptRoutingEngine(OCREngine):
    """Korean model first; pages with almost no Hangul are re-read with an English model.

    The Korean recognizer garbles Latin text and digits (measured: '61,000' -> '6l,ooo'),
    and wrong numbers are the worst possible error for this app.
    """

    name = "paddle"

    def __init__(
        self,
        korean: OCREngine,
        make_english: Callable[[], OCREngine],
        min_hangul_ratio: float = 0.10,
        min_letters: int = 40,
    ) -> None:
        self._korean = korean
        self._make_english = make_english
        self._english: OCREngine | None = None
        self._min_ratio = min_hangul_ratio
        self._min_letters = min_letters
        self.last_language = "ko"

    def recognize(self, image: np.ndarray) -> OCRResult:
        result = self._korean.recognize(image)
        self.last_language = "ko"
        text = result.full_text
        if sum(c.isalpha() for c in text) >= self._min_letters and hangul_ratio(text) < self._min_ratio:
            if self._english is None:
                self._english = self._make_english()  # lazy: only loaded when needed
            self.last_language = "en"
            return self._english.recognize(image)
        return result
