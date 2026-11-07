# OCR accuracy (20 samples: 5 documents x 4 conditions)

Character error rate (CER, lower is better) and character recall (higher is better).
Ground truth: the PDF text layer. Whitespace ignored.

## CER by condition

| Config | clean | lowres | photo | shaky | **all** |
|---|---|---|---|---|---|
| ko-raw | 21.8% | 28.2% | 28.4% | 40.9% | **29.8%** |
| ko-pre | 21.8% | 27.9% | 28.4% | 37.7% | **28.9%** |
| routed-pre | 21.8% | 27.9% | 28.4% | 37.7% | **28.9%** |
| gemini-pre | 15.0% | 26.4% | 24.4% | 22.6% | **22.1%** |

## Character recall by condition

| Config | clean | lowres | photo | shaky | **all** |
|---|---|---|---|---|---|
| ko-raw | 96.4% | 89.5% | 94.1% | 79.4% | **89.9%** |
| ko-pre | 96.4% | 89.8% | 94.1% | 78.0% | **89.6%** |
| routed-pre | 96.4% | 89.8% | 94.1% | 78.0% | **89.6%** |
| gemini-pre | 98.7% | 88.5% | 95.3% | 94.6% | **94.3%** |

## By document

Table-heavy forms have a text layer in a different cell order than OCR reading order,
so their CER is mostly an ordering penalty: read their recall instead.

| Document | Kind | routed-pre CER | routed-pre recall | gemini-pre CER | gemini-pre recall |
|---|---|---|---|---|---|
| moj | table form | 78.9% | 89.9% | 72.4% | 96.5% |
| parttime | plain text | 2.2% | 97.8% | 0.0% | 100.0% |
| seoul_a3 | table form | 23.1% | 83.0% | 16.7% | 90.6% |
| seoul_a | table form | 35.4% | 78.6% | 21.4% | 84.3% |
| student | plain text | 5.1% | 98.6% | 0.0% | 100.0% |

Mean OCR time per page (routed-pre): 1.0 s.

Mean OCR time per page (gemini-pre): 5.5 s.
