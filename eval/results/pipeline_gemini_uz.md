# Pipeline results

Same local model (`qwen2.5:7b`) for both columns. *Baseline* = one plain prompt with the OCR text;
*ClearKo* = clause-by-clause review + rules + quote and number checks.

## Planted problems found (synthetic documents)

| Document | Planted | ClearKo found | Baseline found | ClearKo missed | Baseline missed |
|---|---|---|---|---|---|
| parttime_photo | 11 | **9** | n/a | wage below minimum, confidentiality with damages | - |
| student_photo | 5 | **4** | n/a | wage below minimum | - |

## Blank forms (the right answer is a warning and no red flags)

| Document | Red flags | Warned it is blank |
|---|---|---|

## All runs

| Document | Time | Red flags | High | Quotes not matched to scan |
|---|---|---|---|---|
| parttime_photo | 36 s | 10 | 5 | 0 |
| student_photo | 29 s | 6 | 5 | 0 |
