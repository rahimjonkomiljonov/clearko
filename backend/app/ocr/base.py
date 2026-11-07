from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class OCRLine:
    text: str
    confidence: float
    # Axis-aligned box: x0, y0, x1, y1 in pixels of the image given to the engine.
    bbox: tuple[int, int, int, int]


@dataclass
class OCRResult:
    lines: list[OCRLine] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    @property
    def mean_confidence(self) -> float:
        if not self.lines:
            return 0.0
        return sum(line.confidence for line in self.lines) / len(self.lines)


class OCREngine(ABC):
    """Swappable OCR backend. Takes a BGR (or grayscale) image, returns lines in reading order."""

    name: str
    # False for engines that cannot say how sure they are (a vision LLM): the pipeline then reports
    # no OCR confidence instead of a made-up one.
    has_confidence: bool = True

    @abstractmethod
    def recognize(self, image: np.ndarray) -> OCRResult: ...


def sort_reading_order(lines: list[OCRLine]) -> list[OCRLine]:
    """Group boxes into rows by vertical overlap, then order left-to-right inside each row."""
    ordered = sorted(lines, key=lambda ln: (ln.bbox[1] + ln.bbox[3]) / 2)
    rows: list[list[OCRLine]] = []
    for ln in ordered:
        cy = (ln.bbox[1] + ln.bbox[3]) / 2
        height = max(1, ln.bbox[3] - ln.bbox[1])
        if rows:
            last = rows[-1]
            row_cy = sum((x.bbox[1] + x.bbox[3]) / 2 for x in last) / len(last)
            if abs(cy - row_cy) < 0.5 * height:
                last.append(ln)
                continue
        rows.append([ln])
    return [ln for row in rows for ln in sorted(row, key=lambda x: x.bbox[0])]
