from __future__ import annotations

import numpy as np

from .base import OCREngine, OCRLine, OCRResult, sort_reading_order


def resolve_device(device: str) -> str:
    """'auto' -> 'gpu:0' if this Paddle build can see a CUDA GPU, else 'cpu'."""
    if device != "auto":
        return device
    import paddle

    if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
        return "gpu:0"
    return "cpu"


class PaddleOCREngine(OCREngine):
    name = "paddle"  # PaddleOCREngine(lang="korean" | "en")

    def __init__(
        self,
        use_orientation: bool = False,  # built-in check wrongly rotated 2 of 8 test pages
        device: str = "auto",
        det_limit_side_len: int = 1280,
        lang: str = "korean",
    ) -> None:
        from paddleocr import PaddleOCR  # imported lazily: heavy

        self._ocr = PaddleOCR(
            device=resolve_device(device),
            lang=lang,
            use_doc_orientation_classify=use_orientation,  # fixes 90/180 degree pages
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,  # oneDNN + PIR crashes on CPU with Paddle 3.x
            # Cap detection resolution. On CPU, 1280 was ~40% faster than uncapped for ~5% fewer
            # chars (measured). The mobile det/rec models lost 80%+ of the text; don't use them.
            text_det_limit_side_len=det_limit_side_len,
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
