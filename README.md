# ClearKo

**Understand any Korean document.** Photograph a Korean rental contract, phone plan or part-time job
contract; ClearKo reads it (OCR) and explains it in Uzbek, Russian or English: summary, key facts,
red flags (with the original Korean quoted), and to-dos.

> ClearKo explains documents. It is **not legal advice**.

Status: **Milestones 1 (pipeline CLI), 2 (API), 3 (frontend) and 4 (evaluation) done.** Next: Milestone 5 (polish and deploy). See `clearko-brief.md` for the full plan.

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

## Run the API

```bash
cd backend
pip install -e ".[api]"
python -m uvicorn app.api.main:app --port 8000
```

An analysis takes 45-100 s, too long for one request on a phone, so the API works with **jobs**:

| Call | What it does |
|---|---|
| `POST /api/jobs` (multipart: `files` = 1+ JPG/PNG/WebP/PDF, `lang` = `uz`/`ru`/`en`, optional `doc_type`) | Validates, returns `202 {"job_id", "status"}` at once |
| `GET /api/jobs/{id}` | `{status: queued/running/done/failed, stage, result, error}`; `stage` is e.g. `summarizing`, `reviewing clauses 2/6`, `translating 3/5` |
| `DELETE /api/jobs/{id}` | Deletes the result now |
| `GET /api/health` | `{"status": "ok"}` |

```bash
curl -F "files=@page1.jpg" -F "files=@page2.jpg" -F lang=uz http://localhost:8000/api/jobs
curl http://localhost:8000/api/jobs/<job_id>
```

- **Errors** are `{"detail": {"code", "message"}}` with the message in the user's language
  (`uz`/`ru`/`en`; the Russian and Uzbek texts in `app/messages.py` were written by hand and need a
  native speaker's review). Codes: `bad_lang`, `no_files`, `bad_file`, `heic` (iPhone HEIC photos
  are not supported yet), `too_large` (413), `too_many`, `rate_limited` / `busy` (429, with
  `Retry-After`), `busy` (503, queue full), `not_found` (404). A job that fails reports
  `blurry`, `no_text`, `unsupported`, `explain_failed` or `internal`.
- **Rate limits** (in memory, per client): 10 analyses per hour and 30 per day, plus 500 per day
  for everybody, to protect LLM cost. Behind a reverse proxy set `TRUST_PROXY=true` so the real
  client address is used. All limits are settings, see `.env.example`.
- **One analysis at a time:** OCR and the LLM share one GPU, so jobs go through a single worker;
  at most 4 wait in the queue.
- **Privacy:** uploaded pages are decoded in memory and dropped as soon as the analysis ends;
  results are kept in memory for 15 minutes and then deleted (or earlier with `DELETE`). ClearKo
  writes no document to disk and logs no document text (job logs hold ids, error codes and
  timings only). Starlette may spool a large upload to a temp file for the length of one request.
- File type is checked from the first bytes, not from the name or `Content-Type`.

## Run the web app

```bash
cd frontend
cp .env.example .env.local        # NEXT_PUBLIC_API_URL, default http://localhost:8000
npm install
npm run dev                       # http://localhost:3000   (start the API first)
npm test                          # unit tests for stage parsing, file checks, language
```

Next.js + TypeScript + Tailwind, mobile first. Take a photo (opens the rear camera on a phone) or
pick files, choose uz/ru/en, watch the live progress, read the result (red flags first, each with
the original Korean quote), and delete it with one tap. Installable as a PWA; there is deliberately
**no service worker**, so nothing about a document is cached on the device. HEIC photos are
refused with a hint (iPhone Safari usually converts to JPG when you pick from the gallery).
The Russian and Uzbek interface texts in `frontend/lib/i18n.ts` were written by hand and need a
native speaker's review.

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

**Local model comparison** (same prompts, same documents; set `LLM_MODEL` to switch):

| | `qwen2.5:7b` (default) | `exaone3.5:7.8b` (LG, Korean-specialist, non-commercial licence) |
|---|---|---|
| Rental summary | good | slightly more accurate |
| Part-time contract, time | 44 s | 78 s |
| Planted special terms (uniform deduction, deposit, NDA) | all found | missed in that run |
| Duplicate flags next to rule flags | rare | several |
| Student form summary | correct | said "within legal parameters" for an illegal form |

EXAONE reads Korean better but follows the instructions less well, so it is not the default.

**Fixed along the way:** the "sublet" mistake was caused by our own prompt, which said "do not call
it a sublet": the model repeated the word. Telling it the plain fact (the landlord rents directly to
the tenant) removed it. Lesson: never name the wrong answer in a prompt.

**Known weaknesses** (to be measured properly in Milestone 4):
- The small local model sometimes gets the *story* wrong: the explanation of the broker-fee clause
  is sometimes garbled. The quoted Korean and the numbers are right; the English around them is
  not always.
- **Blank forms** (templates with empty slots) are detected from the PDF text layer and get a
  warning instead of red flags. A *photo* of a blank form is not detected yet.
- Severity from the model varies between runs for the same clause. Keyword floors fix the
  broker-fee, eviction and penalty clauses only.
- Nothing here has been checked by a Korean reader yet. A Korean speaker must verify the OCR and
  the explanations before release, and an Uzbek speaker the Uzbek.

## Evaluation (Milestone 4)

Everything is reproducible from `eval/` (scripts, the synthetic generator, public-form sources).
Documents with personal data stay in git-ignored folders; only synthetic and public material is committed.

```bash
python eval/tools/make_synthetic_parttime.py     # fake part-time contract + student form (planted problems)
python eval/tools/make_ocr_set.py                # 20 OCR samples: 5 pages x 4 photo conditions
cd backend
python ../eval/ocr_cer.py                        # -> eval/results/ocr_cer.md
python ../eval/run_pipeline.py                   # -> eval/results/pipeline.md + review sheets
```

**1. OCR accuracy** (20 samples, ground truth = the PDF's own text layer; full tables in
`eval/results/ocr_cer.md`). Plain-text pages (the contracts) are read almost perfectly, even from a
tilted, shadowed phone photo. Table-heavy government forms score badly on CER only because a PDF
text layer lists table cells in a different order than OCR reads them, so for those read *recall*.

| Page type | CER | Character recall |
|---|---|---|
| Plain text (synthetic contract, student form), 8 samples | 2-5% | 98% |
| Table-heavy forms (3 pages), 12 samples | 23-79% (reading order) | 79-90% |
| By condition, all pages: clean / low-res / photo / shaky | 22 / 28 / 28 / 38% | 96 / 90 / 94 / 78% |

Preprocessing (resize, blur check, deskew) helps only on the shaky samples (CER 41% -> 38%); on
clean photos it changes nothing. The English re-read for Latin pages changes nothing on Korean
documents. Both stay, but they are not where the accuracy comes from. Known limit: on a tilted
photo of a table, line order can scramble (one synthetic photo: CER 15% with 99.8% recall).

**2. Does the pipeline beat "paste it into a model"?** Same local model (`qwen2.5:7b`), same OCR
text. The baseline is one plain prompt ("explain this and point out risks"); ClearKo is the clause
review + rules + checks. Scored on the problems planted in the synthetic documents
(`eval/planted.py`, keyword matching applied the same way to both, and the baseline is given its
whole answer to match in, while ClearKo is only given its red flags).

| Document | Planted | ClearKo | Baseline |
|---|---|---|---|
| Part-time contract, photo | 11 | **10** | 9 |
| Part-time contract, PDF | 11 | **11** | 7 |
| Student work form, photo | 5 | **5** | 3 |
| Student work form, PDF | 5 | **5** | 3 |
| **Total** | 32 | **31 (97%)** | 22 (69%) |

The baseline misses exactly the things that need a rule: the legal minimum wage (it does not know
the 2026 figure), the weekly rest day, and work that started before the permit. It also hides
nothing, which is the point of the other columns: every ClearKo flag carries the original Korean
quote, and all quotes in these runs matched the scan. ClearKo's one miss is the catch-all clause
"anything not agreed follows the employer's instructions" on the photo version.

**3. Blank forms** (the right answer is a warning and no flags): the Seoul and Ministry of Justice
blank leases both gave 0 red flags and the blank-form warning. Before the blank-form check these
printed legal notices were flagged as risks.

**4. Real documents** (private, redacted): the rental contract gives 5 flags (2 high: the early
termination penalty with the broker fee on the tenant, and eviction after noise complaints) and the
phone-plan flyers give 4 (3 high: early termination penalty, visa change and number cancellation,
price rise after the promotion). 26-60 s each on the RTX 4060 Ti.

**What the evaluation found and fixed**
- The PDF version of the contract missed the uniform deduction and the employer-held deposit that
  the photo version found: model judgement varies with its input. Both are now deterministic rules
  (Labor Standards Act articles 20, 22 and 43), so the PDF scores 11/11.
- My first baseline run was unfair: the model client forced JSON output even for free text, which
  made the baseline answer in Chinese, loop, and fail with HTTP 500 on long text. It now runs in plain-text mode.
- An early OCR test used the Arabic edition of a Seoul form as "Korean" ground truth. Replaced.

**Limits of this evaluation (be honest about them)**
- 8 pipeline documents is small, and 4 of them are synthetic, written by me, so the rules were
  written knowing what was planted. The 97% is a check that nothing regressed, not a measure of
  performance on arbitrary contracts. Real contracts (1 rental, 1 phone) are judged only by eye.
- **Nobody who reads Korean has checked the output yet.** The review sheets in
  `eval/results/review/` (public and synthetic documents) and `eval/results/raw/review/`
  (private ones, not committed) are made for that: for each flag a reviewer ticks real problem /
  false alarm / explanation correct / severity right, and lists what was missed.
  Once a Korean speaker fills them in, the precision (false alarms) can finally be reported.
- No hosted-chatbot comparison yet: paste `eval/results/chatbot_prompt.txt` into ChatGPT/Gemini/Claude and
  save the answer to compare by hand. The local-model baseline above stands in for it.
- Uzbek and Russian output are not evaluated beyond number checks; they need native review.
