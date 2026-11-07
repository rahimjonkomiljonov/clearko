# ClearKo architecture

How a photo of a Korean document becomes an explanation in Uzbek, Russian or English, and where
each safety check sits. The diagram is Mermaid, so GitHub renders it.

## The pipeline

```mermaid
flowchart TD
    subgraph Browser["Phone browser: Next.js PWA (Vercel)"]
        UI["Pick language, take or choose photos"]
        POLL["Poll progress, show result"]
        DEL["Delete result"]
    end

    subgraph API["FastAPI service (one GPU machine)"]
        V["Validate: type sniffed from file bytes,<br/>size and page limits, rate limits"]
        Q["Job queue: one worker, max 4 waiting"]
        MEM[("Result in memory,<br/>deleted after 15 min")]
    end

    subgraph Worker["Worker thread: analyze()"]
        direction TB
        L["Load pages: PDF text layer, or image"]
        P["Preprocess (OpenCV): resize, blur check, deskew"]
        O["OCR (PaddleOCR): Korean model,<br/>English re-read for Latin pages,<br/>rotation retry if unsure"]
        C["Classify: rental / phone plan / part-time"]
        E1["LLM call 1: summary, key facts, to-dos"]
        CL["Split into clauses and label them:<br/>printed article, hand-written special term,<br/>attached notice"]
        E2["LLM call 2: judge each added clause by id"]
        R["Rules, no model: minimum wage, rest day,<br/>insurance, cash, deposit, deductions, ..."]
        G["Guards: quote must exist in the scan,<br/>numbers must exist in the scan,<br/>answer must be in the right language"]
        M["Merge: rule flags win over model flags<br/>about the same line"]
        T["Translate: Russian by gemma3:4b,<br/>Uzbek by NLLB-200 in its own process,<br/>every number re-checked"]
    end

    UI -->|"POST /api/jobs"| V --> Q --> L
    L --> P --> O --> C --> E1 --> CL --> E2 --> G
    C --> R --> M
    G --> M --> T --> MEM
    POLL -->|"GET /api/jobs/id"| MEM
    DEL -->|"DELETE /api/jobs/id"| MEM
    Q -.->|"stage text"| POLL
```

## What each part is for

| Part | Where | Why it exists |
|---|---|---|
| Content-sniffed upload checks | `backend/app/api/main.py` | The file extension and `Content-Type` are chosen by the client; the first bytes are not. |
| Job queue (one worker) | `backend/app/api/jobs.py` | OCR and the LLM share one GPU, and an analysis takes 20-100 s, too long for a single phone request. |
| Rate limiter | `backend/app/api/limits.py` | Per client (hour and day) and a global daily cap, to protect LLM cost. |
| Blur check | `backend/app/preprocess/` | A blurry photo gives wrong digits; better to ask for a new photo than to explain garbage. |
| Script-routed OCR | `backend/app/ocr/routing.py` | The Korean model garbles Latin text and digits (`61,000` read as `6l,ooo`); pages that are mostly Latin are re-read with the English model. |
| Clause labels | `backend/app/explain/clauses.py` | The small model explained a printed standard article backwards, so printed articles and attached notices are not reviewed; only clauses added to *this* contract are. |
| Clause-by-clause review | `backend/app/explain/judge.py` | A single "find the risks" prompt skips clauses; judging every added clause by id cannot. |
| Rules | `backend/app/explain/rules.py` | Some facts are not a matter of model opinion: 9,000 KRW is below the 2026 minimum wage of 10,320 KRW. Rules are deterministic and tested. |
| Quote and number guards | `backend/app/explain/` | Every flag shows the scan's own Korean text, and a number that is not in the scan is marked as unverified. |
| NLLB worker process | `backend/app/explain/nllb_worker.py` | `torch` and PaddleOCR cannot share a Windows process (different cuDNN DLLs), so Uzbek translation runs in a separate process and frees the GPU afterwards. |
| In-memory results | `backend/app/api/jobs.py` | Nothing about a document is written to disk, a database or a log. |

## Where the trust boundaries are

- **Browser to API:** CORS allows only the configured origin; the production frontend sends a
  Content-Security-Policy that lets the page talk only to itself and the API.
- **Behind a proxy:** with `TRUST_PROXY=true` the rate limiter trusts the *last* `X-Forwarded-For`
  entry (added by the one trusted proxy), never the first (client-controlled).
- **LLM provider:** with the default Ollama provider the text never leaves the machine. With
  `LLM_PROVIDER=gemini` it goes to Google, and the privacy page says so (it asks `/api/health`).

## Swappable parts

- **OCR** sits behind `OCREngine` (`backend/app/ocr/base.py`): `recognize(image) -> OCRResult`.
  Only PaddleOCR is implemented. EasyOCR was not added, because it needs `torch`, which conflicts
  with Paddle (see above).
- **LLM** sits behind `LLMClient` (`backend/app/explain/llm_client.py`): Ollama (default) and Gemini.
- **Translators** sit behind `StringTranslator` (`backend/app/explain/translate.py`).
