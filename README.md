# ClearKo

**Understand any Korean document.** Photograph a Korean rental contract, phone plan or part-time job
contract; ClearKo reads it (OCR) and explains it in Uzbek, Russian or English: summary, key facts,
red flags (with the original Korean quoted), and to-dos.

> ClearKo explains documents. It is **not legal advice**.

Status: **Milestone 1 (pipeline CLI) in progress.** See `clearko-brief.md` for the full plan.

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
- **Explain:** one prompt per document type, structured JSON out, one retry on invalid JSON.
  Every quoted Korean passage is checked against the OCR text; unverifiable quotes are flagged.
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

## Measured so far (first rental sample, 8 phone-style pages, RTX 4060 Ti)

| Setup | All 8 pages |
|---|---|
| PaddleOCR on CPU (Ryzen 5) | ~6-15 min |
| PaddleOCR on GPU | ~3 s |

Evaluation set and results table: coming in Milestone 4.
