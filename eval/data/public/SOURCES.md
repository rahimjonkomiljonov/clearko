# Public sample documents (downloaded, not committed)

All three are blank standard forms from public bodies, with a text layer (so they skip OCR).
Download with `curl -A "Mozilla/5.0" -o <name> <url>` (moj.go.kr needs cookies: `-L -c jar -b jar`).

| File | Source |
|---|---|
| `seoul_monthly_rent_a.pdf` | https://global.seoul.go.kr/contents/bdmg/cont/1670834212972.pdf (standard lease, monthly rent with deposit) |
| `seoul_monthly_rent_b.pdf` | https://global.seoul.go.kr/contents/bdmg/cont/1670834212982.pdf |
| `moj_standard_lease.pdf` | https://www.moj.go.kr/bbs/moj/118/491743/download.do (Ministry of Justice, Korean + English) |

They are templates, so they test the "blank form" path (no red flags, a warning instead).
