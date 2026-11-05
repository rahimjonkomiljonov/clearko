from __future__ import annotations

import numpy as np

from .base import OCREngine, OCRLine, OCRResult, sort_reading_order


class PaddleOCREngine(OCREngine):
    name = "paddle"

    def __init__(self, use_orientation: bool = True) -> None:
        from paddleocr import PaddleOCR  # imported lazily: heavy

        self._ocr = PaddleOCR(
            lang="korean",
            use_doc_orientation_classify=use_orientation,  # fixes 90/180 degree pages
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,  # oneDNN + PIR crashes on CPU with Paddle 3.x
            # Cap detection resolution: ~40% faster on A4 photos, ~5% fewer chars (measured).
            # The mobile det/rec models were faster still but lost 80%+ of the text.
            text_det_limit_side_len=1280,
            text_det_limit_type="max",
        )

    def recognize(self, image: np.ndarray) -> OCRResult:
        if image.ndim == 2:
            import cv2

            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        lines: list[OCRLine] = []
        for page in self._ocr.predict(image):
            texts = page["rec_texts"]
            scores = page["rec_scores"]
            polys = page["rec_polys"]
            for text, score, poly in zip(texts, scores, polys):
                if not text.strip():
                    continue
                pts = np.asarray(poly)
                x0, y0 = pts.min(axis=0)
                x1, y1 = pts.max(axis=0)
                lines.append(OCRLine(text, float(score), (int(x0), int(y0), int(x1), int(y1))))
        return OCRResult(sort_reading_order(lines))
