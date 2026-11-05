"""Build the OCR test set: 5 Korean documents x 4 photo conditions = 20 samples.

Ground truth is the PDF's own text layer, so it is exact (no hand transcription).
Source PDFs: the synthetic contracts (eval/tools/make_synthetic_parttime.py) and the public
blank lease forms (eval/data/public, see SOURCES.md).

    python eval/tools/make_ocr_set.py        # writes eval/data/ocr_set/ (git-ignored, rebuildable)
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pymupdf as fitz

sys.path.insert(0, str(Path(__file__).parent))
from make_synthetic_parttime import phone_photo

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "ocr_set"

# (name, pdf, page index)
DOCS = [
    ("seoul_a", DATA / "public/seoul_monthly_rent_a.pdf", 0),
    ("seoul_a3", DATA / "public/seoul_monthly_rent_a.pdf", 2),
    ("moj", DATA / "public/moj_standard_lease.pdf", 0),
    ("parttime", DATA / "synthetic/parttime_contract.pdf", 0),
    ("student", DATA / "synthetic/student_confirmation.pdf", 0),
]


def render(page: fitz.Page, dpi: int) -> np.ndarray:
    pix = page.get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2BGR)


def lowres(img: np.ndarray) -> np.ndarray:
    """A small screenshot / forwarded-chat image: low resolution, then upscaled by the viewer."""
    h, w = img.shape[:2]
    small = cv2.resize(img, (int(w * 0.5), int(h * 0.5)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 55])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR) if ok else small


def shaky(img: np.ndarray) -> np.ndarray:
    """Slight motion blur and a 2 degree tilt, as from a hand-held phone."""
    k = np.zeros((7, 7), np.float32)
    k[3, :] = 1 / 7
    blurred = cv2.filter2D(img, -1, k)
    h, w = img.shape[:2]
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), 2.0, 1.0)
    return cv2.warpAffine(blurred, rot, (w, h), borderValue=(255, 255, 255))


CONDITIONS = {
    "clean": lambda img, seed: img,
    "photo": phone_photo,
    "lowres": lambda img, seed: lowres(img),
    "shaky": lambda img, seed: shaky(img),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for seed, (name, pdf, idx) in enumerate(DOCS, 1):
        if not pdf.exists():
            sys.exit(f"missing {pdf} (see eval/data/public/SOURCES.md, or run make_synthetic_parttime.py)")
        page = fitz.open(pdf)[idx]
        (OUT / f"{name}.txt").write_text(page.get_text(), encoding="utf-8")
        base = render(page, 170)
        for cond, fn in CONDITIONS.items():
            cv2.imwrite(str(OUT / f"{name}__{cond}.jpg"), fn(base, seed), [cv2.IMWRITE_JPEG_QUALITY, 90])
            n += 1
    print(f"wrote {n} samples + ground truth to {OUT}")


if __name__ == "__main__":
    main()
