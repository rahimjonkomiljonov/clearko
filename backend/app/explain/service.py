from __future__ import annotations

from .llm_client import LLMClient
from .parse import ParseError, parse_output, verify_numbers, verify_quotes
from .prompts import build_prompt, build_retry_prompt
from .schemas import DISCLAIMER, DocType, Explanation, LLMOutput


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
    schema = LLMOutput.model_json_schema()
    raw = client.generate(system, messages, schema)
    try:
        output = parse_output(raw)
    except ParseError as first_error:
        messages += [("model", raw), ("user", build_retry_prompt(str(first_error)))]
        output = parse_output(client.generate(system, messages, schema))  # second failure propagates

    warnings: list[str] = []
    unverified = verify_quotes(output, ocr_text)
    if unverified:
        warnings.append(f"{unverified} quoted passage(s) could not be found in the scan")
    wrong = verify_numbers(output, ocr_text)
    if wrong:
        warnings.append(f"{wrong} item(s) mention a number that is not in the scan. Check them.")
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
