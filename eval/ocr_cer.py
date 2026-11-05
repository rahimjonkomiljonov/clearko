"""OCR character error rate (CER) per engine configuration on the eval OCR set.

    python eval/tools/make_ocr_set.py            # once
    cd backend && .venv/Scripts/python ../eval/ocr_cer.py

Configurations compared:
  ko-raw      Korean PaddleOCR model on the unprocessed image
  ko-pre      Korean model after preprocessing (resize, blur check, deskew)
  routed-pre  what ClearKo ships: preprocessing + Korean model + English re-read of Latin pages

Writes eval/results/ocr_cer.md and eval/results/raw/ocr_cer.json (raw is git-ignored).
Ground truth is the PDF text layer. CER ignores whitespace; "recall" ignores character order.
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))

import cv2

from app.metrics import cer, char_recall
from app.ocr import get_engine
from app.ocr.orient import recognize_upright
from app.preprocess import BlurryImageError, preprocess

SET = ROOT / "data" / "ocr_set"
RESULTS = ROOT / "results"


def main() -> None:
    samples = sorted(SET.glob("*__*.jpg"))
    if not samples:
        sys.exit("no samples: run eval/tools/make_ocr_set.py first")

    routed = get_engine("paddle", "auto")  # ScriptRoutingEngine(korean, english)
    ko = routed._korean  # the plain Korean engine, shared so models load once
    engines = {"ko-raw": (ko, False), "ko-pre": (ko, True), "routed-pre": (routed, True)}

    rows = []
    for path in samples:
        name, cond = path.stem.split("__")
        truth = (SET / f"{name}.txt").read_text(encoding="utf-8")
        img = cv2.imread(str(path))
        for label, (engine, pre) in engines.items():
            row = {"doc": name, "cond": cond, "config": label, "chars": len("".join(truth.split()))}
            try:
                work = preprocess(img).image if pre else img
            except BlurryImageError:
                row.update(status="rejected_blurry", cer=None, recall=None, seconds=0.0)
                rows.append(row)
                continue
            t0 = time.perf_counter()
            result, _ = recognize_upright(engine, work)
            row.update(
                status="ok",
                cer=cer(truth, result.full_text),
                recall=char_recall(truth, result.full_text),
                seconds=time.perf_counter() - t0,
            )
            rows.append(row)
            print(f"{path.name:28} {label:11} CER {row['cer']:.3f}  recall {row['recall']:.3f}", flush=True)

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "raw").mkdir(exist_ok=True)
    (RESULTS / "raw" / "ocr_cer.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    (RESULTS / "ocr_cer.md").write_text(report(rows, len(samples)), encoding="utf-8")
    print("wrote", RESULTS / "ocr_cer.md")


# Table-heavy government forms: the PDF text layer lists cells in its own order, which differs
# from OCR reading order, so CER on them mostly measures ordering. Recall is the fair number.
FORMS = {"seoul_a", "seoul_a3", "moj"}


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def report(rows: list[dict], n_samples: int) -> str:
    configs = list(dict.fromkeys(r["config"] for r in rows))
    conds = list(dict.fromkeys(r["cond"] for r in rows))
    out = [f"# OCR accuracy ({n_samples} samples: 5 documents x {len(conds)} conditions)\n"]
    out.append("Character error rate (CER, lower is better) and character recall (higher is better).")
    out.append("Ground truth: the PDF text layer. Whitespace ignored.\n")

    def cell(rs: list[dict], key: str) -> str:
        ok = [r[key] for r in rs if r["status"] == "ok"]
        rej = sum(r["status"] != "ok" for r in rs)
        txt = f"{mean(ok) * 100:.1f}%" if ok else "n/a"
        return txt + (f" ({rej} rejected)" if rej else "")

    for key, title in (("cer", "CER by condition"), ("recall", "Character recall by condition")):
        out.append(f"## {title}\n")
        out.append("| Config | " + " | ".join(conds) + " | **all** |")
        out.append("|---|" + "---|" * (len(conds) + 1))
        for c in configs:
            by = defaultdict(list)
            for r in rows:
                if r["config"] == c:
                    by[r["cond"]].append(r)
            cells = [cell(by[k], key) for k in conds]
            allr = [r for r in rows if r["config"] == c]
            out.append(f"| {c} | " + " | ".join(cells) + f" | **{cell(allr, key)}** |")
        out.append("")

    out.append("## By document (routed-pre)\n")
    out.append("Table-heavy forms have a text layer in a different cell order than OCR reading order,")
    out.append("so their CER is mostly an ordering penalty: read their recall instead.\n")
    out.append("| Document | Kind | CER | Recall |")
    out.append("|---|---|---|---|")
    for d in dict.fromkeys(r["doc"] for r in rows):
        rs = [r for r in rows if r["doc"] == d and r["config"] == "routed-pre"]
        kind = "table form" if d in FORMS else "plain text"
        out.append(f"| {d} | {kind} | {cell(rs, 'cer')} | {cell(rs, 'recall')} |")
    secs = [r["seconds"] for r in rows if r["config"] == "routed-pre" and r["status"] == "ok"]
    out.append(f"\nMean OCR time per page (routed-pre): {mean(secs):.1f} s.")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    main()
