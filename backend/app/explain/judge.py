"""Clause-by-clause review. Every clause gets its own answer, so nothing is skipped."""

from __future__ import annotations

import re
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from .clauses import ARTICLE, NOTICE, SPECIAL, Clause, batch_clauses
from .llm_client import LLMClient
from .parse import ParseError, extract_json
from .prompts import build_judge_prompt
from .schemas import DocType, RedFlag, Severity


class ClauseJudgement(BaseModel):
    id: int
    title: str = ""
    meaning: str = ""
    concern: str = "none"  # none | low | medium | high
    why: str = ""


class ClauseBatch(BaseModel):
    items: list[ClauseJudgement]


_HAN = re.compile(r"[一-鿿㐀-䶿]")  # Chinese ideographs: the model drifts into them
_HANGUL = re.compile(r"[가-힣]")
MAX_HANGUL = 12  # a short quoted term is fine, a Korean sentence is not


def _parse_batch(raw: str) -> list[ClauseJudgement]:
    try:
        items = ClauseBatch.model_validate(extract_json(raw)).items
    except ValidationError as e:
        raise ParseError(f"JSON does not match the schema: {e.errors()[0]['msg']}") from None
    for item in items:
        text = f"{item.title}{item.meaning}{item.why}"
        if _HAN.search(text):
            raise ParseError("The answer contains Chinese text. Write ONLY in English")
        if len(_HANGUL.findall(text)) > MAX_HANGUL:
            raise ParseError("The answer is in Korean. Write title, meaning and why in ENGLISH")
    return items


_RANK = {Severity.LOW: 0, Severity.MEDIUM: 1, Severity.HIGH: 2}
# Terms that are costly or take rights away whatever the model says (it rated the same broker
# fee clause HIGH in one run and MEDIUM in the next). Matched on text without spaces, because OCR
# of handwriting often drops them. A floor only raises a severity the model already assigned.
_FLOORS: list[tuple[re.Pattern[str], Severity]] = [
    (re.compile(r"중개(수수료|보수).{0,12}(임차인|세입자).{0,6}부담|(임차인|세입자).{0,12}중개(수수료|보수)"),
     Severity.HIGH),  # tenant pays the broker fee
    (re.compile(r"퇴거|명도"), Severity.HIGH),  # eviction
    (re.compile(r"위약금"), Severity.MEDIUM),  # penalty money
]


def _title(j: ClauseJudgement) -> str:
    """The model sometimes leaves the title empty: fall back to the start of its explanation."""
    for text in (j.title, j.meaning, j.why):
        text = text.strip()
        if text:
            return text if len(text) <= 60 else text[:57].rstrip() + "..."
    return "Clause to check"


def _apply_floor(severity: Severity, text: str) -> Severity:
    squashed = re.sub(r"\s+", "", text)
    for pattern, floor in _FLOORS:
        if pattern.search(squashed) and _RANK[floor] > _RANK[severity]:
            severity = floor
    return severity


_TAGS = {
    ARTICLE: "(printed standard article) ",
    SPECIAL: "(hand-written special term) ",
}


def _ask(client: LLMClient, doc_type: DocType, clauses: list[Clause]) -> list[ClauseJudgement]:
    system, user = build_judge_prompt(
        doc_type, [(c.id, _TAGS.get(c.kind, "") + c.text) for c in clauses]
    )
    schema = ClauseBatch.model_json_schema()
    raw = client.generate(system, [("user", user)], schema)
    try:
        return _parse_batch(raw)
    except ParseError as err:
        retry = [
            ("user", user),
            ("model", raw),
            ("user", f"Unusable answer: {err}. Return ONLY the corrected JSON."),
        ]
        return _parse_batch(client.generate(system, retry, schema))


def judge_clauses(
    client: LLMClient,
    doc_type: DocType,
    clauses: list[Clause],
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[list[RedFlag], list[int]]:
    """Return (red flags in document order, ids of clauses the model never answered).

    Printed standard articles and attached notices are not reviewed: the 7B model explained them wrongly (it said a
    landlord "cannot terminate" under a clause that says the landlord can), and a wrong
    explanation is worse than none. The risks are in the hand-written and other clauses.
    """
    clauses = [c for c in clauses if c.kind not in (ARTICLE, NOTICE)]
    by_id = {c.id: c for c in clauses}
    judged: dict[int, ClauseJudgement] = {}

    def run(batch: list[Clause]) -> None:
        try:
            for item in _ask(client, doc_type, batch):
                if item.id in by_id and item.id not in judged:
                    judged[item.id] = item
        except ParseError:
            pass  # the clauses stay unanswered and are retried below

    batches = batch_clauses(clauses)
    for n, batch in enumerate(batches, 1):
        run(batch)
        if on_progress:
            on_progress(n, len(batches))

    missing = [c for c in clauses if c.id not in judged]
    for batch in batch_clauses(missing, max_items=4):  # one more try, in small batches
        run(batch)
    unanswered = [c.id for c in clauses if c.id not in judged]

    flags: list[RedFlag] = []
    for c in clauses:
        j = judged.get(c.id)
        if j is None or j.concern not in ("low", "medium", "high"):
            continue
        explanation = " ".join(x for x in (j.meaning.strip(), j.why.strip()) if x)
        severity = _apply_floor(Severity(j.concern), c.text)
        flags.append(
            RedFlag(
                title=_title(j),
                explanation=explanation,
                original_text=c.text,
                quote_verified=True,  # the clause text IS the OCR text
                severity=severity,
            )
        )
    return flags, unanswered
