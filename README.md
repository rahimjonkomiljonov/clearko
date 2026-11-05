# ClearKo

**Understand any Korean document.** Photograph a Korean rental contract, phone plan or part-time job
contract; ClearKo reads it (OCR) and explains it in Uzbek, Russian or English: summary, key facts,
red flags (with the original Korean quoted), and to-dos.

> ClearKo explains documents. It is **not legal advice**.

Status: **Milestone 1 (pipeline CLI) done, waiting for review.** See `clearko-brief.md` for the full plan.

## Pipeline

```
image/PDF -> preprocess (OpenCV) -> OCR (PaddleOCR) -> classify -> LLM (Ollama, local) -> JSON
```

- **Preprocess:** resize, blur rejection, deskew. Crop and contrast are optional (they did not help
  on the first sample set).
- **OCR:** PaddleOCR behind an `OCREngine` interface. Korean model first; pages that are mostly Latin
  script are re-read with an English model (the Korean model garbles digits: `61,000` -> `6l,ooo`).
  Rotated pages are retried at 90/180/270 degrees when confidence is low.
- **PDFs with a text layer** skip OCR.
- **Explain:** an overview call (summary, key facts, to-dos), then a **clause-by-clause review**:
  the text is split into clauses and the model judges every added clause by id, so nothing is
  skipped. Printed articles of the standard government form (제N조) are *not* reviewed: the small
  local model explained them wrongly, and a wrong explanation is worse than none. The quote shown
  for a flag is the scan's own text. Numbers in the output are checked against the scan.
- **Rules:** objective checks that need no model, for part-time documents: wage below the legal
  minimum (10,320 KRW in 2026, 10,700 KRW from 1 Jan 2027), no weekly rest day, no insurance, cash
  pay, no copy of the contract, no overtime pay, student hours above the limit, empty required
  fields, work started before the permit. Update the minimum wage every August (`prompts.py`).
- **Privacy:** no storage, no document text in logs (only with `--ocr-only` / `--debug`). The default
  LLM runs locally through Ollama, so documents never leave your machine. A Gemini client exists as
  an optional cloud provider (free tier content may be used by Google; not used by default).

## Setup (backend)

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate        # Windows; use bin/activate on Linux/macOS
pip install -e ".[ocr,pdf,llm,dev]"
# NVIDIA GPU (recommended, ~100x faster than CPU): replace the CPU build
pip uninstall -y paddlepaddle
pip install paddlepaddle-gpu==3.3.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
cp ../.env.example ../.env
# Local LLM: install Ollama (https://ollama.com), then e.g.:  ollama pull qwen2.5:7b
ollama pull gemma3:4b                                  # Russian translation

# Uzbek translation (Meta NLLB-200, ~5 GB of downloads). torch 2.7.1 matches Paddle's CUDA libs:
pip install "torch==2.7.1" --index-url https://download.pytorch.org/whl/cu126
pip install -e ".[uz]"
```

## Languages

| Language | How it is produced | Status |
|---|---|---|
| English | `qwen2.5:7b` analysis (clause by clause) | Good, still over-flags some standard clauses |
| Russian | English analysis, translated by `gemma3:4b` | Good in tests |
| Uzbek | English analysis, translated sentence by sentence by NLLB-200 (1.3B) | Fluent in tests; **needs review by an Uzbek speaker** |

Every translated number is checked against the English one; a string whose numbers changed stays
in English. `qwen2.5:7b` and `gemma3:4b` cannot write usable Uzbek, which is why NLLB is used.

**Licence note:** the NLLB-200 weights are CC-BY-NC 4.0, so Uzbek translation with NLLB is for
**non-commercial use only**. Set `UZ_TRANSLATOR=llm` to avoid it (Uzbek quality is then poor).
NLLB runs in its own worker process: torch and PaddleOCR cannot share a Windows process (both load
different cuDNN DLLs), and this also frees the GPU memory when the run ends.

## Run the CLI

```bash
python -m app.cli path/to/page1.jpg path/to/page2.jpg --lang uz --out result.json
python -m app.cli folder_of_pages/ --lang en
python -m app.cli contract.pdf --ocr-only        # OCR + detected type only, no LLM / key needed
```

Exit codes: 0 ok, 2 bad input, 3 unusable document (blurry / no text / unsupported type), 4 LLM failure.

## Tests

```bash
cd backend && python -m pytest -q
```

## Measured so far (RTX 4060 Ti 8 GB, Ryzen 5, English output, `qwen2.5:7b`)

| Setup | All 8 pages |
|---|---|
| PaddleOCR on CPU (Ryzen 5) | ~6-15 min |
| PaddleOCR on GPU | ~3 s |

| Sample | Pages | OCR | Explanation | What it found |
|---|---|---|---|---|
| Rental contract (real, redacted) | 8 | 3.7 s | ~70 s (en), ~100 s (uz, includes starting NLLB) | broker fee on tenant HIGH, eviction on noise complaints HIGH, repairs, sewer, cleaning, 1/N water fee MEDIUM |
| Phone plan flyers (real, English) | 2 | 2.4 s | 25 s | price rise 22,900 -> 61,000 KRW HIGH, visa-change cancellation HIGH, 12-month lock, 95-day cancel ban |
| Part-time contract (synthetic photo) | 1 | 0.6 s | 44 s | 11 planted problems: 10-11 found (wage, rest day, insurance, cash, no copy, overtime, 50% pay cut, deductions, deposit, NDA) |
| Student work confirmation (synthetic photo) | 1 | 0.5 s | 19 s | 33 h/week, wage, started before permit, empty school/permit fields, cash: all found |

Synthetic documents are made by `eval/tools/make_synthetic_parttime.py` (fake names; the planted
problems are listed in `eval/data/synthetic/*_expected.md`).

**Known weaknesses** (to be measured properly in Milestone 4):
- The small local model sometimes gets the *story* wrong: it called the basement rental a
  "sublet", and its explanation of the broker-fee clause is garbled. The quoted Korean and the
  numbers are right; the English around them is not always.
- **Blank forms are over-flagged**: the printed explanation of penalties on an empty student work
  form is reported as a problem (2 HIGH flags on a blank form).
- Severity from the model varies between runs for the same clause. Keyword floors fix the
  broker-fee, eviction and penalty clauses only.
- Nothing here has been checked by a Korean reader yet. A Korean speaker must verify the OCR and
  the explanations before release, and an Uzbek speaker the Uzbek.

Evaluation set and results table: coming in Milestone 4.
