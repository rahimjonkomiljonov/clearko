# ClearKo: a case study

*Photograph a Korean document, get a plain-language explanation in Uzbek, Russian or English.*

## The problem

International students and workers in Korea routinely sign documents they cannot fully read:
a monthly-rent lease with a deposit, a phone plan with a price that jumps after a promotion, a
part-time job contract. The costly mistakes hide in a few clauses, and they are in Korean legal
language. Translators handle words, not meaning: "who pays the broker fee if I move out early" is
a question about *consequences*, and a literal translation does not answer it.

The target user is Uzbek-speaking, which matters technically: Uzbek is a language most small
models write badly.

## What was built

A mobile-first web app and an API. A user photographs the pages; the system reads them (OCR),
decides what kind of document it is, and returns a summary, key facts, red flags (each with the
original Korean quote), a to-do list and the text it read, so the user can check it against the
paper. Nothing is stored: pages live in memory for the length of the analysis and the result
for 15 minutes at most. The default model runs locally, so documents never leave the machine.

Stack: Next.js and Tailwind, FastAPI, OpenCV, PaddleOCR, a local LLM through Ollama, and Meta's NLLB-200
for Uzbek. 147 backend and 10 frontend tests.

## The decisions that mattered, and the evidence

| Decision | Alternatives | Evidence |
|---|---|---|
| OCR on the GPU | CPU | 8 pages: 6-15 min on the CPU, about 3 s on an RTX 4060 Ti. Without a GPU the app is not usable on a phone. |
| English re-read for Latin-script pages | Korean model only | The Korean model reads `61,000` as `6l,ooo`. Phone-plan flyers are full of prices. |
| `qwen2.5:7b` as the default model | `exaone3.5:7.8b` (LG's Korean-specialist model) | EXAONE reads Korean slightly better, but took 78 s vs 44 s, missed planted problems, and called an illegal student work form "within legal parameters". It also answered in Korean and over-flagged attachments. Not adopted. |
| Uzbek through NLLB-200, translating from English | Ask the local models to write Uzbek | `qwen` and `gemma3` cannot write usable Uzbek. NLLB is fluent in tests but its weights are non-commercial (CC-BY-NC), a licence limit documented in the README. |
| Review every added clause by id | One "find the risks" prompt | A single prompt skips clauses. On the planted-problem test the plain prompt found 22 of 32 problems and the clause review found 31 (see Results). |
| Do not review the printed standard articles | Review everything | The small model explained printed Article 4 *backwards* (it said the landlord could not terminate). A wrong explanation is worse than none, so only clauses added to the contract are judged. |
| Deterministic rules next to the model | Model only | A minimum-wage check is arithmetic, not opinion. The plain prompt missed it on every document, and the clause review missed several such facts (wage, rest day, employer-held deposit) until they became rules. A fixed seed and keyword floors reduced the run-to-run variation in severity. |
| Show the scan's own Korean text with every flag | Show the model's paraphrase | A quote that cannot be found in the scan is hidden, so the page never shows invented Korean. |
| Let a Gemini vision model read pages as an optional OCR engine | PaddleOCR only | Mean recall 94.3% vs 89.6% and 0% error on the plain-text contracts, with no GPU needed, which is what makes a free always-on demo possible. But it looped on one photo (fixed with a repeat cap) and silently dropped 40% of one low-resolution page (not fixed), so it is a demo path, not the default. |
| Jobs with polling | One long request | An analysis takes 20-100 s; mobile connections drop. |

## What went wrong (and what it taught)

- **The model called a basement unit a "sublet".** The cause was the project's own prompt, which
  said "do not call it a sublet". The model repeated the word. Telling it the plain fact (the
  landlord rents directly to the tenant) removed the error. *Never name the wrong answer in a prompt.*
- **Installing the translation library broke OCR.** `torch` and PaddleOCR load different cuDNN
  libraries and cannot share a Windows process. Pinning versions did not fix it; running
  translation in a separate worker process did, and it frees the GPU memory afterwards.
- **The first comparison against a plain prompt was unfair.** The model client forced JSON output
  even for free text, so the baseline answered in Chinese, looped and crashed on long inputs.
  Found by reading the baseline's output instead of trusting its score; fixed and rerun.
- **A test document was in the wrong language.** One OCR "Korean" page was the Arabic edition of
  a Seoul form. The error rate looked terrible until the page was opened.
- **Blank government forms were flagged as risky.** The printed legal notices on an empty template
  looked like red flags. Blank forms are now detected and get a warning instead.
- **Same contract, different answer.** The PDF version of a synthetic contract missed two clauses
  its photo version had caught: model judgement varies with its input. Both are now rules, and the
  PDF scores 11 of 11.

## Results

OCR (20 samples, ground truth = the PDF text layer): plain-text pages 2-5% character error and
98% of the true characters recovered, even from a tilted, shadowed phone photo. Table-heavy
government forms score 79-90% recall; their error rate mostly measures reading order, not
recognition. Preprocessing only helped on shaky photos.

Explanation quality on documents with planted problems (same local model for both):

| | Planted problems found |
|---|---|
| Plain prompt with the OCR text | 22 of 32 (69%) |
| ClearKo | 31 of 32 (97%) |

Blank forms: 0 false red flags on both government templates. Time: 20-60 s per document in English
on a consumer GPU; about 80-100 s with Uzbek translation.

## Limits (read before quoting any number above)

- **The test set is small and partly synthetic.** Eight documents, four of them written by the author with
  known planted problems. The rules were written knowing what was planted, so 97% shows that nothing
  regressed, not how the system performs on arbitrary contracts.
- **No Korean speaker has verified the output yet.** The review sheets for that are generated
  (`eval/results/review/`). Until they are filled in, the false-alarm rate is unknown.
- **No native review of the Uzbek and Russian** interface and error texts, or of the translations.
- **No real Korean phone-plan contract was tested**, only English flyers.
- **The comparison with a hosted chatbot has not been run.** The local plain-prompt baseline stands in.
- **Not deployed.** The container files are written but have never been built.
- This is an explainer, **not legal advice**, and it says so on every result.

## What would come next

1. A Korean-speaking reviewer fills in the review sheets, giving a measured precision.
2. A larger set of real, consented, redacted documents, especially phone-plan contracts.
3. Native review of Uzbek and Russian.
4. Deploy (GPU host or tunnel) and watch real use.
5. Revisit the model choice yearly; the minimum wage in the rules must be updated every August.
