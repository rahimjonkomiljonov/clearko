"""Planted problems in the synthetic documents, and a keyword check for whether an explanation
found them. The documents are fake and every problem in them was put there on purpose, so this
is an objective recall measure (see data/synthetic/*_expected.md for the plain-English list).

A problem counts as found when its pattern matches the text of the explanation (case-insensitive).
The patterns are deliberately loose so a baseline is not penalised for wording; they are applied
the same way to ClearKo's red flags and to the baseline's free-text answer.
"""

from __future__ import annotations

import re

PLANTED: dict[str, dict[str, str]] = {
    "parttime": {
        "wage below minimum": r"minimum wage|minimum hourly|최저임금|below the (legal )?minimum",
        "no weekly rest day / holiday pay": r"rest day|weekly (rest|holiday)|holiday pay|day off|주휴",
        "no overtime / night pay": r"overtime|night|연장|야간",
        "paid in cash": r"cash|현금",
        "no social insurance": r"insurance|보험",
        "no copy of the contract": r"copy|교부|keeps? the contract|employer (keeps|holds)",
        "50% wage cut if leaving": r"50 ?%|half of|5\s*0%|half (of )?(the |your )?(last|final)",
        "uniform / breakage deducted": r"uniform|유니폼|breakage|damaged (item|goods|product)",
        "300,000 KRW deposit": r"deposit|보증금",
        "confidentiality with damages": r"confidential|disclos|non-disclosure|외부에 알리",
        "'follow employer's orders' catch-all": r"instruct|지시|not (specified|covered|agreed)|catch-all",
    },
    "student": {
        "33 h/week over the limit": r"33|hour limit|weekly hours|too many hours|exceed|above (the )?(legal )?limit",
        "started before the permit": r"before the (work )?permit|without (a |the )?permit|already (working|started)|"
        r"started (work|working)|허가",
        "school confirmation empty": r"school|university|international office|담당자|미기재|not (filled|completed)|empty",
        "wage below minimum": r"minimum wage|minimum hourly|최저임금|below the (legal )?minimum",
        "paid in cash": r"cash|현금",
    },
}


def found(doc: str, text: str) -> dict[str, bool]:
    """Which planted problems of `doc` does `text` mention?"""
    return {name: bool(re.search(pat, text, re.IGNORECASE)) for name, pat in PLANTED[doc].items()}


def recall(doc: str, text: str) -> float:
    hits = found(doc, text)
    return sum(hits.values()) / len(hits)
