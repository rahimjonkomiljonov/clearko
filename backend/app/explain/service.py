from __future__ import annotations

from collections.abc import Callable

from .clauses import split_clauses
from .judge import judge_clauses
from .llm_client import LLMClient
from .parse import ParseError, parse_output, verify_numbers, verify_quotes
from .prompts import build_overview_prompt, build_prompt, build_retry_prompt
from .schemas import DISCLAIMER, DocType, Explanation, LLMOutput, RedFlag, Severity
from .translate import StringTranslator, translate_explanation

_ORDER = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
MAX_FLAGS = 10
MAX_LOW_FLAGS = 3


def _overview(client: LLMClient, system: str, user: str) -> LLMOutput:
    """One call for summary / key facts / todos, with one retry if the JSON is unusable."""
    messages = [("user", user)]
    schema = LLMOutput.model_json_schema()
    raw = client.generate(system, messages, schema)
    try:
        return parse_output(raw)
    except ParseError as first_error:
        messages += [("model", raw), ("user", build_retry_prompt(str(first_error)))]
        return parse_output(client.generate(system, messages, schema))  # second failure propagates


def _select_flags(flags: list[RedFlag]) -> list[RedFlag]:
    """Most serious first; keep every high/medium (up to a cap) and only a few low ones."""
    ranked = sorted(flags, key=lambda f: _ORDER[f.severity])  # stable: keeps document order
    serious = [f for f in ranked if f.severity != Severity.LOW]
    low = [f for f in ranked if f.severity == Severity.LOW][:MAX_LOW_FLAGS]
    return (serious + low)[: max(MAX_FLAGS, len(serious))]


def explain(
    ocr_text: str,
    doc_type: DocType,
    lang: str,
    client: LLMClient,
    ocr_confidence: float | None = None,
    *,
    translator: LLMClient | StringTranslator | None = None,
    clause_review: bool = True,
    translate: bool = True,
    on_stage: Callable[[str], None] | None = None,
) -> Explanation:
    """Overview + clause-by-clause red flags (English), then translate to `lang` if needed."""

    def stage(msg: str) -> None:
        if on_stage:
            on_stage(msg)

    warnings: list[str] = []

    stage("summarizing")
    if clause_review:
        system, user = build_overview_prompt(doc_type, ocr_text)
    else:  # legacy single call: the model writes everything, including red flags
        system, user = build_prompt(doc_type, "en", ocr_text)
    output = _overview(client, system, user)
    unverified = verify_quotes(output, ocr_text)
    if unverified:
        warnings.append(f"{unverified} quoted passage(s) could not be found in the scan")

    if clause_review:
        clauses = split_clauses(ocr_text)
        flags, unanswered = judge_clauses(
            client, doc_type, clauses, lambda n, total: stage(f"reviewing clauses {n}/{total}")
        )
        output.red_flags = _select_flags(flags)
        if unanswered:
            warnings.append(f"{len(unanswered)} clause(s) could not be reviewed automatically")

    wrong = verify_numbers(output, ocr_text)
    if wrong:
        warnings.append(f"{wrong} item(s) mention a number that is not in the scan. Check them.")
    if ocr_confidence is not None and ocr_confidence < 0.8:
        warnings.append("The photo was hard to read. Check numbers against the original.")

    result = Explanation(
        **output.model_dump(),
        doc_type=doc_type,
        language=lang,
        disclaimer=DISCLAIMER[lang],
        ocr_confidence=ocr_confidence,
        warnings=warnings,
    )
    if lang != "en" and translate:
        stage(f"translating to {lang}")
        result, kept = translate_explanation(
            result, lang, translator or client, lambda n, total: stage(f"translating {n}/{total}")
        )
        if kept:
            result.warnings.append(f"{kept} text(s) were left in English (translation unreliable)")
    return result
