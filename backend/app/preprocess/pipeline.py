from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import steps


class BlurryImageError(ValueError):
    def __init__(self, score: float):
        super().__init__(f"Image too blurry (score={score:.1f})")
        self.score = score


@dataclass
class PreprocessResult:
    image: np.ndarray
    applied: list[str] = field(default_factory=list)
    blur_score: float = 0.0
    skew_angle: float = 0.0


def preprocess(
    img: np.ndarray,
    *,
    max_side: int = 2400,
    blur_threshold: float = 60.0,
    crop: bool = False,
    contrast: bool = False,
) -> PreprocessResult:
    """Resize -> blur check -> [perspective crop] -> deskew -> [contrast].

    Crop and contrast are off by default: on the first rental sample (8 pages) resize alone was
    as accurate, and the crop dropped 38% of one page's text. Re-evaluate on the full eval set.

    Raises BlurryImageError if the image is too blurry to OCR.
    """
    applied: list[str] = []

    resized = steps.resize_max_side(img, max_side)
    if resized is not img:
        applied.append("resize")
    img = resized

    score = steps.blur_score(img)
    if score < blur_threshold:
        raise BlurryImageError(score)

    if crop:
        quad = steps.find_document_quad(img)
        if quad is not None:
            img = steps.perspective_crop(img, quad)
            applied.append("perspective_crop")

    angle = steps.estimate_skew_angle(img)
    if abs(angle) >= 0.2:
        img = steps.rotate(img, angle)
        applied.append("deskew")

    if contrast:
        img = steps.enhance_contrast(img)
        applied.append("contrast")

    return PreprocessResult(image=img, applied=applied, blur_score=score, skew_angle=angle)
