# Pipeline results

Same local model (`qwen2.5:7b`) for both columns. *Baseline* = one plain prompt with the OCR text;
*ClearKo* = clause-by-clause review + rules + quote and number checks.

## Planted problems found (synthetic documents)

| Document | Planted | ClearKo found | Baseline found | ClearKo missed | Baseline missed |
|---|---|---|---|---|---|
| parttime_photo | 11 | **10** | n/a | confidentiality with damages | - |
| student_photo | 5 | **5** | n/a | - | - |
| parttime_pdf | 11 | **11** | n/a | - | - |
| student_pdf | 5 | **5** | n/a | - | - |

## Blank forms (the right answer is a warning and no red flags)

| Document | Red flags | Warned it is blank |
|---|---|---|
| seoul_blank | 0 | yes |
| moj_blank | 0 | yes |

## All runs

| Document | Time | Red flags | High | Quotes not matched to scan |
|---|---|---|---|---|
| parttime_photo | 11 s | 10 | 5 | 0 |
| student_photo | 9 s | 6 | 5 | 0 |
| parttime_pdf | 13 s | 13 | 6 | 0 |
| student_pdf | 8 s | 6 | 5 | 0 |
| seoul_blank | 7 s | 0 | 0 | 0 |
| moj_blank | 3 s | 0 | 0 | 0 |
