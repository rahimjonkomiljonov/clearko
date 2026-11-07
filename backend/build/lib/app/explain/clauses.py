"""Split OCR text into reviewable clauses. The clause text is the OCR text itself, so any quote
built from a clause is verbatim by construction."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Lines that start a new clause: 제3조, (1), 1. / 1), bullets, circled numbers, notes.
_START = re.compile(r"^(제\s*\d+\s*조|\(\s*\d+\s*\)|\d{1,2}\s*[.)]\s|[•ㅇ※▶◦\-]\s*|[①-⑳])")
_PAGE = re.compile(r"^-{2,}\s*page\s*\d+\s*-{2,}$", re.IGNORECASE)
_SPECIAL_START = "특약사항"
_SPECIAL_END = ("본계약을증명", "계약당사자가", "서명또는기명")

MIN_CHARS = 15  # shorter chunks are labels / OCR crumbs
MAX_CHUNK_CHARS = 320  # long articles are split on line boundaries
MAX_CLAUSES = 90


ARTICLE = "article"  # printed 제N조 body of a standard form
SPECIAL = "special"  # hand-written special terms (특약사항)
NOTICE = "notice"  # attachments after the contract: broker sheet, legal information
OTHER = "other"
_ARTICLE_START = re.compile(r"^제\s*\d+\s*조")


@dataclass
class Clause:
    id: int
    text: str
    kind: str = OTHER


def _squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _useful(text: str) -> bool:
    letters = sum(c.isalpha() for c in text)
    return len(text.replace(" ", "")) >= MIN_CHARS and letters >= MIN_CHARS * 0.6


def split_clauses(text: str) -> list[Clause]:
    chunks: list[tuple[str, str]] = []  # (text, kind)
    buf: list[str] = []
    in_special = False
    in_article = False  # set by the first 제N조 line, cleared by the special terms
    after_contract = False  # set once the special terms / signature block is over

    def flush() -> None:
        if buf:
            kind = NOTICE if after_contract else ARTICLE if in_article else OTHER
            chunks.append((" ".join(buf).strip(), kind))
            buf.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line or _PAGE.match(line):
            continue
        sq = _squash(line)
        if _SPECIAL_START in sq and len(sq) < 20:
            flush()
            in_special, in_article = True, False
            continue
        if in_special:
            if any(m in sq for m in _SPECIAL_END):
                in_special = False
                flush()
                after_contract = True
                continue
            flush()  # one handwritten special term per line
            chunks.append((line, SPECIAL))
            continue
        if _START.match(line) or sum(len(x) for x in buf) > MAX_CHUNK_CHARS:
            flush()
        if _ARTICLE_START.match(line):
            in_article = True
        buf.append(line)
    flush()

    useful = [(c, k) for c, k in chunks if _useful(c)]
    if not any(k == SPECIAL for _, k in useful):
        # No special-terms section was found, so we cannot tell where the printed form ends:
        # do not treat anything as a standard printed article or an attachment.
        useful = [(c, OTHER) for c, _ in useful]
    return [Clause(i, c, k) for i, (c, k) in enumerate(useful[:MAX_CLAUSES], 1)]


def batch_clauses(clauses: list[Clause], max_chars: int = 2200, max_items: int = 10) -> list[list[Clause]]:
    batches: list[list[Clause]] = []
    cur: list[Clause] = []
    size = 0
    for c in clauses:
        if cur and (size + len(c.text) > max_chars or len(cur) >= max_items):
            batches.append(cur)
            cur, size = [], 0
        cur.append(c)
        size += len(c.text)
    if cur:
        batches.append(cur)
    return batches
