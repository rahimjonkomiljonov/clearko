"""ClearKo pipeline CLI:  python -m app.cli PATH [PATH ...] --lang uz --out result.json

PATH may be an image, a PDF, or a folder of page images. Document text is never printed unless
--ocr-only or --debug is given.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import get_settings
from .explain import DocType, LLMError, classify, get_llm_client
from .explain.parse import ParseError
from .ocr import get_engine
from .pipeline import NoTextFound, UnsupportedDocument, analyze, load_pages, read_pages
from .preprocess import BlurryImageError, ImageDecodeError

MESSAGES = {  # user-facing messages for the failure cases in the brief
    "blurry": "The photo is too blurry. Hold the phone steady, use good light and retake it.",
    "no_text": "No text was found. Make sure the whole page is in the photo and try again.",
    "unsupported": "This does not look like a rental, phone plan or part-time job document.",
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="clearko", description=__doc__)
    p.add_argument("paths", nargs="+", type=Path, help="image(s), PDF(s) or folder(s) of pages")
    p.add_argument("--lang", choices=["uz", "ru", "en"], default="en")
    p.add_argument("--out", type=Path, help="write the JSON result here (default: stdout)")
    p.add_argument("--ocr-only", action="store_true", help="print OCR text + detected type only")
    p.add_argument("--doc-type", choices=[t.value for t in DocType if t != DocType.UNSUPPORTED])
    p.add_argument("--debug", action="store_true", help="also print OCR text to stderr")
    return p


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    settings = get_settings()

    try:
        pages = load_pages(args.paths)
    except ImageDecodeError:
        log("Could not open one of the images.")
        return 2
    if not pages:
        log("No images or PDFs found at the given path(s).")
        return 2
    log(f"{len(pages)} page(s) loaded")

    engine = get_engine(settings.ocr_engine, settings.ocr_device)
    forced = DocType(args.doc_type) if args.doc_type else None
    try:
        if args.ocr_only:
            reading = read_pages(
                pages, engine, max_side=settings.max_image_side,
                blur_threshold=settings.blur_threshold,
            )
            detected, scores = classify(reading.text)
            conf = f"{reading.confidence:.3f}" if reading.confidence is not None else "n/a"
            log(f"type={detected.value} confidence={conf} timings={reading.timings}")
            log(f"scores={ {k.value: v for k, v in scores.items()} }")
            print(reading.text)
            return 0
        llm = get_llm_client(
            settings.llm_provider, settings.llm_api_key, settings.llm_model, settings.llm_base_url
        )
        translator = None
        if settings.llm_translate_model and args.lang != "en":
            translator = get_llm_client(
                settings.llm_provider, settings.llm_api_key,
                settings.llm_translate_model, settings.llm_base_url,
            )
        result, reading = analyze(
            pages, args.lang, engine, llm, doc_type=forced,
            max_side=settings.max_image_side, blur_threshold=settings.blur_threshold,
            translator=translator, on_stage=log,
        )
    except BlurryImageError:
        log(MESSAGES["blurry"])
        return 3
    except NoTextFound:
        log(MESSAGES["no_text"])
        return 3
    except UnsupportedDocument:
        log(MESSAGES["unsupported"])
        return 3
    except (LLMError, ParseError) as e:
        log(f"Explanation failed: {e}")
        return 4

    if args.debug:
        log(reading.text)
    log(f"done: type={result.doc_type.value} timings={ {k: round(v, 1) for k, v in reading.timings.items()} }")
    payload = json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
        log(f"wrote {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
