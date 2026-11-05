from __future__ import annotations

from .llm_client import LLMClient
from .parse import ParseError, parse_output, verify_quotes
from .prompts import build_prompt, build_retry_prompt
from .schemas import DISCLAIMER, DocType, Explanation


def explain(
    ocr_text: str,
    doc_type: DocType,
    lang: str,
    client: LLMClient,
    ocr_confidence: float | None = None,
) -> Explanation:
    """Ask the LLM for a structured explanation; retry once if the JSON is unusable."""
    system, user = build_prompt(doc_type, lang, ocr_text)
    messages = [("user", user)]
    raw = client.generate(system, messages)
    try:
        output = parse_output(raw)
    except ParseError as first_error:
        messages += [("model", raw), ("user", build_retry_prompt(str(first_error)))]
        output = parse_output(client.generate(system, messages))  # second failure propagates

    warnings: list[str] = []
    unverified = verify_quotes(output, ocr_text)
    if unverified:
        warnings.append(f"{unverified} quoted passage(s) could not be found in the scan")
    if ocr_confidence is not None and ocr_confidence < 0.8:
        warnings.append("The photo was hard to read. Check numbers against the original.")

    return Explanation(
        **output.model_dump(),
        doc_type=doc_type,
        language=lang,
        disclaimer=DISCLAIMER[lang],
        ocr_confidence=ocr_confidence,
        warnings=warnings,
    )
