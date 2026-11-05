# ClearKo: Project Brief

## What we're building
ClearKo is a mobile-first web app (PWA) that helps international students and workers in Korea understand Korean documents. The user photographs a document, ClearKo reads it with OCR, and an LLM explains it in Uzbek, Russian, or English. It highlights key facts, risky clauses, and what the user needs to do next.

Tagline: "Understand any Korean document."

Primary users: Central Asian (especially Uzbek-speaking) students and workers in Korea.

## Goals
1. A working, deployed demo that a real user can open on a phone and use in under a minute.
2. A clean computer vision + language pipeline with measured quality (not just "it works").
3. A portfolio-ready repo: README, architecture diagram, results table, case study.

## Scope (v1)
Support only these document types at first:
- Rental contracts (월세/전세, 원룸)
- Mobile phone plan contracts
- Part-time job contracts

Out of scope for v1: user accounts, payments, native apps, other document types, offline mode.

## User flow
1. Open the site on a phone, pick a language (Uzbek / Russian / English).
2. Take a photo or upload an image (multiple pages allowed).
3. App preprocesses the image, runs OCR, and detects the document type.
4. App shows the result:
   - **Summary**: 3-5 plain sentences.
   - **Key facts**: e.g. deposit, monthly rent, contract period, penalties, notice period.
   - **Red flags**: unusual or risky clauses, each with a short explanation and the original Korean text.
   - **To-do / deadlines**: what the user should do or watch for.
   - **Original text** (collapsible), so the user can verify against the source.
5. Uploaded images and extracted text are deleted right after processing (no storage).

## Architecture
- **Frontend**: Next.js (TypeScript), Tailwind, mobile-first. Camera capture via `<input type="file" accept="image/*" capture>`.
- **Backend**: Python FastAPI service.
  - Preprocessing with OpenCV (grayscale, deskew, perspective crop, contrast).
  - OCR with PaddleOCR (Korean). Keep the OCR layer behind an interface so EasyOCR or a vision LLM can be swapped in for comparison.
  - LLM explanation step via an API call (provider configurable by env var).
- **Prompts**: one prompt template per document type, returning structured JSON (summary, key_facts, red_flags, todos) that the frontend renders.
- **Config**: all keys and settings in `.env`, with a `.env.example` committed.
- **Deploy**: frontend on a free tier (e.g. Vercel), backend on a small server or container.

## Quality and safety requirements
- Show a clear disclaimer: ClearKo explains documents and is not legal advice.
- Always show the original Korean text next to claims about it.
- Add rate limiting to protect LLM costs.
- Never log document contents.
- Handle bad input gracefully (blurry photo, non-document, unsupported type) with a helpful message.

## Evaluation (important for the portfolio)
- Create `eval/` with a small test set of 15-20 anonymized sample documents and ground-truth notes.
- Script that reports OCR character error rate per OCR engine.
- Script that runs the full pipeline and saves outputs for manual review by a Korean speaker.
- Results table in the README comparing ClearKo against a general chatbot on the same documents.

## Suggested repo layout
```
clearko/
  frontend/        # Next.js app
  backend/         # FastAPI app
    app/
      ocr/         # OCR interface + engines
      preprocess/  # OpenCV steps
      explain/     # prompts + LLM client
      api/         # routes
  eval/            # test set, scripts, results
  docs/            # architecture diagram, case study
  README.md
```

## Milestones
1. **Pipeline CLI**: image in, structured JSON out, with no UI yet. Test on the sample set.
2. **Backend API**: FastAPI endpoint wrapping the pipeline.
3. **Frontend**: upload flow, result screens, language switcher.
4. **Evaluation**: scripts and results table.
5. **Polish and deploy**: rate limiting, error states, privacy note, deployment.
6. **Docs**: README, architecture diagram, case study.

## Working instructions for Claude Code
- Start with milestone 1 and ask before moving on to the next milestone.
- Keep the code simple and typed; add tests for the preprocessing and JSON parsing.
- Prefer small commits with clear messages.
- Before adding a new dependency, explain why it's needed.
- Update the README as features land.
