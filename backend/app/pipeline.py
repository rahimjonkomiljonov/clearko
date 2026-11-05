"""image(s) -> preprocess -> OCR -> classify -> explain. No document content is ever logged."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .explain import DocType, Explanation, LLMClient, classify, explain
from .explain.translate import StringTranslator
from .ocr import OCREngine
from .ocr.orient import recognize_upright
from .preprocess import decode_image, preprocess

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
MIN_TEXT_LAYER_CHARS = 80  # a PDF page with less text than this is treated as a scan


class UnsupportedDocument(ValueError):
    """Text was read but it is not one of the supported document types."""


class NoTextFound(ValueError):
    """OCR found (almost) no text: not a document, or the photo is unusable."""


@dataclass
class Page:
    source: str
    image: np.ndarray | None = None
    text: str | None = None  # set when the file already has a text layer


@dataclass
class Reading:
    text: str
    confidence: float | None
    pages: int
    ocr_pages: int
    timings: dict[str, float] = field(default_factory=dict)


def natural_key(p: Path) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def load_pages(paths: list[Path]) -> list[Page]:
    """Expand files/folders into pages. PDFs need the optional `pdf` extra (pymupdf)."""
    files: list[Path] = []
    for p in paths:
        files += sorted((f for f in p.iterdir() if f.is_file()), key=natural_key) if p.is_dir() else [p]
    pages: list[Page] = []
    for f in files:
        suffix = f.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            pages.append(Page(f.name, image=decode_image(f.read_bytes())))
        elif suffix == ".pdf":
            pages += _load_pdf(f)
        # other file types are ignored on purpose (e.g. notes, json from earlier runs)
    return pages


def _load_pdf(path: Path) -> list[Page]:
    return _pdf_pages(path.name, path)


def pages_from_bytes(name: str, data: bytes) -> list[Page]:
    """One uploaded file (image or PDF) -> pages. Raises ImageDecodeError for unreadable images."""
    if data[:5] == b"%PDF-":
        return _pdf_pages(name, data)
    return [Page(name, image=decode_image(data))]


def _pdf_pages(name: str, source: Path | bytes) -> list[Page]:
    import pymupdf

    doc = pymupdf.open(source) if isinstance(source, Path) else pymupdf.open(stream=source, filetype="pdf")
    out: list[Page] = []
    with doc:
        for i, page in enumerate(doc, 1):
            text = page.get_text().strip()
            page_name = f"{name}#{i}"
            if len(text) >= MIN_TEXT_LAYER_CHARS:
                out.append(Page(page_name, text=text))
            else:
                pix = page.get_pixmap(dpi=200)
                img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
                bgr = img[:, :, [2, 1, 0]] if pix.n == 3 else img[:, :, 0]
                out.append(Page(page_name, image=np.ascontiguousarray(bgr)))
    return out


def read_pages(
    pages: list[Page],
    engine: OCREngine,
    *,
    max_side: int = 2400,
    blur_threshold: float = 60.0,
    on_stage: Callable[[str], None] | None = None,
) -> Reading:
    """Preprocess + OCR every page that needs it. Raises BlurryImageError on a blurry photo."""
    texts: list[str] = []
    confs: list[float] = []
    t_pre = t_ocr = 0.0
    ocr_pages = 0
    for n, page in enumerate(pages, 1):
        if page.text is not None:
            texts.append(page.text)
            continue
        assert page.image is not None
        t0 = time.perf_counter()
        prepared = preprocess(page.image, max_side=max_side, blur_threshold=blur_threshold)
        t1 = time.perf_counter()
        result, _ = recognize_upright(engine, prepared.image)
        t_pre += t1 - t0
        t_ocr += time.perf_counter() - t1
        ocr_pages += 1
        if result.lines:
            texts.append(result.full_text)
            confs.append(result.mean_confidence)
        if on_stage:
            on_stage(f"page {n}/{len(pages)} read")
    text = "\n\n".join(f"--- page {i} ---\n{t}" for i, t in enumerate(texts, 1))
    confidence = sum(confs) / len(confs) if confs else None
    return Reading(
        text, confidence, len(pages), ocr_pages, {"preprocess_s": t_pre, "ocr_s": t_ocr}
    )


def analyze(
    pages: list[Page],
    lang: str,
    engine: OCREngine,
    llm: LLMClient,
    *,
    doc_type: DocType | None = None,
    max_side: int = 2400,
    blur_threshold: float = 60.0,
    translator: LLMClient | StringTranslator | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> tuple[Explanation, Reading]:
    reading = read_pages(
        pages, engine, max_side=max_side, blur_threshold=blur_threshold, on_stage=on_stage
    )
    if len(reading.text.replace("-", "").split()) < 5:
        raise NoTextFound("Almost no text was found in the image")
    detected, _ = classify(reading.text)
    chosen = doc_type or detected
    if chosen == DocType.UNSUPPORTED:
        raise UnsupportedDocument("Not a supported document type")
    t0 = time.perf_counter()
    result = explain(
        reading.text, chosen, lang, llm, reading.confidence, translator=translator, on_stage=on_stage
    )
    reading.timings["llm_s"] = time.perf_counter() - t0
    return result, reading
