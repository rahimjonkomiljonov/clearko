# Pipeline results

Same local model (`qwen2.5:7b`) for both columns. *Baseline* = one plain prompt with the OCR text;
*ClearKo* = clause-by-clause review + rules + quote and number checks.

## Planted problems found (synthetic documents)

| Document | Planted | ClearKo found | Baseline found | ClearKo missed | Baseline missed |
|---|---|---|---|---|---|
| parttime_photo | 11 | **10** | 9 | 'follow employer's orders' catch-all | wage below minimum, no weekly rest day / holiday pay |
| student_photo | 5 | **5** | 3 | - | started before the permit, wage below minimum |
| parttime_pdf | 11 | **11** | 7 | - | wage below minimum, no weekly rest day / holiday pay, 50% wage cut if leaving, 'follow employer's orders' catch-all |
| student_pdf | 5 | **5** | 3 | - | started before the permit, wage below minimum |

## Blank forms (the right answer is a warning and no red flags)

| Document | Red flags | Warned it is blank |
|---|---|---|
| seoul_blank | 0 | yes |
| moj_blank | 0 | yes |

## All runs

| Document | Time | Red flags | High | Quotes not matched to scan |
|---|---|---|---|---|
| parttime_photo | 42 s | 10 | 5 | 0 |
| student_photo | 20 s | 6 | 5 | 0 |
| parttime_pdf | 58 s | 11 | 6 | 0 |
| student_pdf | 23 s | 6 | 5 | 0 |
| seoul_blank | 10 s | 0 | 0 | 0 |
| moj_blank | 21 s | 0 | 0 | 0 |
| rental_real | 42 s | 5 | 2 | 0 |
| phone_real | 27 s | 4 | 3 | 0 |
