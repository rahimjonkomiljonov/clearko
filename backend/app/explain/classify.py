"""Keyword-based document-type detection. Cheap, deterministic, runs before any LLM call."""

from __future__ import annotations

import re

from .schemas import DocType

# Weighted keywords, matched on whitespace-stripped lowercase text (OCR often drops spaces).
KEYWORDS: dict[DocType, dict[str, int]] = {
    DocType.RENTAL: {
        "임대차": 3, "임대인": 3, "임차인": 3, "보증금": 2, "월세": 2, "전세": 2, "차임": 2,
        "중개대상물": 2, "확정일자": 2, "전입신고": 2, "원상회복": 1, "계약갱신": 1,
        "leasecontract": 3, "landlord": 2, "tenant": 2, "securitydeposit": 2, "monthlyrent": 2,
    },
    DocType.PHONE_PLAN: {
        "요금제": 3, "통신": 1, "이동통신": 3, "가입신청": 2, "약정": 2, "위약금": 2,
        "단말기": 2, "번호이동": 3, "유심": 3, "데이터": 1, "부가서비스": 2, "선택약정": 3,
        "phoneplan": 3, "simcard": 3, "numberportability": 3, "unlimitedcalls": 2,
        "hotspot": 2, "5g": 1, "plan": 1, "earlytermination": 2,
    },
    DocType.PART_TIME: {
        "근로계약": 3, "근로자": 2, "사업주": 2, "시급": 2, "시간제취업": 3, "단시간근로": 3,
        "최저임금": 2, "주휴": 2, "근로시간": 2, "휴게시간": 2, "사회보험": 1, "임금지급": 2,
        "part-time": 2, "parttime": 2, "workinghours": 1, "hourlywage": 2, "employer": 1,
        "workpermit": 2,
    },
}

MIN_SCORE = 5  # below this the document is treated as unsupported / not a document
MIN_MARGIN = 2  # winner must beat the runner-up by this much


def _normalise(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def score_types(text: str) -> dict[DocType, int]:
    norm = _normalise(text)
    return {
        doc_type: sum(w for kw, w in kws.items() if kw in norm)
        for doc_type, kws in KEYWORDS.items()
    }


def classify(text: str) -> tuple[DocType, dict[DocType, int]]:
    scores = score_types(text)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    (best, best_score), (_, second_score) = ranked[0], ranked[1]
    if best_score < MIN_SCORE or best_score - second_score < MIN_MARGIN:
        return DocType.UNSUPPORTED, scores
    return best, scores
