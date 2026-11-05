"""Clause-by-clause review. Every clause gets its own answer, so nothing is skipped."""

from __future__ import annotations

import re
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from .clauses import Clause, batch_clauses
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


def _parse_batch(raw: str) -> list[ClauseJudgement]:
    try:
        items = ClauseBatch.model_validate(extract_json(raw)).items
    except ValidationError as e:
        raise ParseError(f"JSON does not match the schema: {e.errors()[0]['msg']}") from None
    for item in items:
        if _HAN.search(f"{item.title}{item.meaning}{item.why}"):
            raise ParseError("The answer contains Chinese text. Write ONLY in English")
    return items


def _ask(client: LLMClient, doc_type: DocType, clauses: list[Clause]) -> list[ClauseJudgement]:
    system, user = build_judge_prompt(doc_type, [(c.id, c.text) for c in clauses])
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
    """Return (red flags in document order, ids of clauses the model never answered)."""
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
        flags.append(
            RedFlag(
                title=j.title.strip() or j.meaning.strip()[:50],
                explanation=explanation,
                original_text=c.text,
                quote_verified=True,  # the clause text IS the OCR text
                severity=Severity(j.concern),
            )
        )
    return flags, unanswered
