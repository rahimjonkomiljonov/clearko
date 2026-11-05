"""Turn raw LLM text into validated output and verify its quotes against the OCR text."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher

from pydantic import ValidationError

from .schemas import LLMOutput


class ParseError(ValueError):
    """Model output was not valid JSON matching the schema. Message is safe to show the model."""


_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def extract_json(raw: str) -> dict:
    text = _FENCE.sub("", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fall back to the outermost {...} in case the model added prose around the JSON.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ParseError("No JSON object found in the response") from None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e.msg} at position {e.pos}") from None
    if not isinstance(data, dict):
        raise ParseError("Top-level JSON value must be an object")
    return data


def parse_output(raw: str) -> LLMOutput:
    data = extract_json(raw)
    try:
        return LLMOutput.model_validate(data)
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
        raise ParseError(f"JSON does not match the schema: {problems}") from None


def _squash(text: str) -> str:
    """Remove whitespace and common punctuation: OCR drops/adds spaces, so compare without them."""
    return re.sub(r"[\s·.,;:·'\"“”‘’()\[\]]+", "", text)


def quote_in_text(quote: str, source: str, min_ratio: float = 0.85) -> bool:
    """True if the quote appears in the source, tolerating whitespace and small OCR errors."""
    q, s = _squash(quote), _squash(source)
    if not q:
        return False
    if q in s:
        return True
    if len(q) < 6:  # too short for fuzzy matching to mean anything
        return False
    match = SequenceMatcher(None, q, s, autojunk=False).find_longest_match(0, len(q), 0, len(s))
    return match.size / len(q) >= min_ratio


def verify_quotes(output: LLMOutput, source_text: str) -> int:
    """Mark each original_text as verified or not. Returns the number of unverified quotes.

    A model quote that is not in the scan is never shown as if it were the original.
    """
    unverified = 0
    for item in [*output.key_facts, *output.red_flags]:
        if item.original_text is None or not item.original_text.strip():
            item.original_text = None
            continue
        item.quote_verified = quote_in_text(item.original_text, source_text)
        if not item.quote_verified:
            unverified += 1
    return unverified
