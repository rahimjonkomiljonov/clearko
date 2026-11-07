"""OCR with a vision LLM (Gemini). No GPU and no PaddlePaddle needed, so the backend can run on a
small CPU server. Trade-offs: the page image LEAVES the machine (free tier: the provider may use
it), and a language model can silently "correct" text. Measure it with eval/ocr_cer.py before trusting it.
"""

from __future__ import annotations

import re

import cv2
import numpy as np

from ..explain.llm_client import GeminiClient, LLMError
from .base import OCREngine, OCRLine, OCRResult

INSTRUCTION = (
    "Transcribe ALL the text in this photo of a document, exactly as written, in reading order, "
    "one line of text per visual line. The text is mostly Korean. Rules: do not translate, "
    "summarise, correct, complete or explain anything; keep every number, date, amount and "
    "punctuation mark exactly as printed; keep empty brackets like [ ] and ( ) as they are; "
    "if a part is unreadable write [?]. Output only the transcription as plain text, with no "
    "markdown and no comments."
)
_FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


MAX_SAME_LINE = 6  # a real page repeats a line a few times ("년", "월" date fields), not hundreds


def cap_repeats(lines: list[str], limit: int = MAX_SAME_LINE) -> list[str]:
    """Drop the 7th and later copies of an identical line. A vision model sometimes falls into a
    loop and repeats a line hundreds of times; measured once: 731 lines for a page of about 60."""
    seen: dict[str, int] = {}
    out = []
    for line in lines:
        seen[line] = seen.get(line, 0) + 1
        if seen[line] <= limit:
            out.append(line)
    return out


class GeminiOCREngine(OCREngine):
    name = "gemini"
    has_confidence = False

    def __init__(self, client: GeminiClient, jpeg_quality: int = 90) -> None:
        self._client = client
        self._quality = jpeg_quality

    def recognize(self, image: np.ndarray) -> OCRResult:
        ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, self._quality])
        if not ok:
            raise LLMError("could not encode the page image")
        text = _FENCE.sub("", self._client.transcribe(buf.tobytes(), INSTRUCTION).strip())
        h, w = image.shape[:2]
        rows = cap_repeats([ln.strip() for ln in text.splitlines() if ln.strip()])
        step = max(1, h // max(1, len(rows)))
        # The model gives no boxes: lines get evenly spaced ones, which keeps the model's own
        # (reading) order. Confidence is a placeholder; the pipeline ignores it (has_confidence).
        return OCRResult([OCRLine(t, 1.0, (0, i * step, w, (i + 1) * step)) for i, t in enumerate(rows)])
