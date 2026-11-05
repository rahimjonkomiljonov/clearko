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
    return "".join(c for c in text if not _SKIP.match(c))


_SKIP = re.compile(r"[\s·.,;:'\"“”‘’()\[\]]")


def _squash_with_map(text: str) -> tuple[str, list[int]]:
    """Squashed text plus, for each squashed char, its index in the original text."""
    chars, index = [], []
    for i, c in enumerate(text):
        if not _SKIP.match(c):
            chars.append(c)
            index.append(i)
    return "".join(chars), index


def locate_quote(quote: str, source: str, min_ratio: float = 0.85) -> str | None:
    """Return the passage of `source` that the quote refers to, exactly as written in the source.

    Tolerates whitespace/punctuation differences and small OCR or rewording errors. Returns None
    if no passage matches well enough, so a made-up quote is never shown as original text.
    """
    q = _squash(quote)
    s, index = _squash_with_map(source)
    if not q or not s:
        return None
    pos = s.find(q)
    if pos >= 0:
        last = pos + len(q) - 1
    else:
        if len(q) < 6:  # too short for fuzzy matching to mean anything
            return None
        # Anchor on the longest common block, then score the whole region around it, so one
        # inserted/dropped character does not split the quote into two failed halves.
        anchor = SequenceMatcher(None, q, s, autojunk=False).find_longest_match(0, len(q), 0, len(s))
        start = max(0, anchor.b - anchor.a)
        window = s[start : start + len(q) + len(q) // 4]
        blocks = [b for b in SequenceMatcher(None, q, window, autojunk=False).get_matching_blocks() if b.size]
        if not blocks or sum(b.size for b in blocks) / len(q) < min_ratio:
            return None
        pos = start + blocks[0].b
        last = start + blocks[-1].b + blocks[-1].size - 1
    return source[index[pos] : index[last] + 1]


def quote_in_text(quote: str, source: str, min_ratio: float = 0.85) -> bool:
    return locate_quote(quote, source, min_ratio) is not None


def verify_quotes(output: LLMOutput, source_text: str) -> int:
    """Replace each original_text with the matching passage of the scan, or mark it unverified.

    Returns the number of quotes that could not be found. A quote that is not in the scan is
    never shown as if it were the original.
    """
    unverified = 0
    for item in [*output.key_facts, *output.red_flags]:
        if item.original_text is None or not item.original_text.strip():
            item.original_text = None
            continue
        found = locate_quote(item.original_text, source_text)
        item.quote_verified = found is not None
        if found is not None:
            item.original_text = found
        else:
            unverified += 1
    return unverified


_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> set[str]:
    """Numbers as digit strings without thousands separators: '5,000,000원' -> '5000000'."""
    return {m.group().rstrip(",").replace(",", "") for m in _NUMBER.finditer(text)}


def verify_numbers(output: LLMOutput, source_text: str) -> int:
    """Flag items that state a number which does not occur anywhere in the scan.

    Catches the worst LLM failure for this app: a plausible but wrong amount or date.
    Returns the number of flagged items.
    """
    known = numbers_in(source_text)
    flagged = 0
    for fact in output.key_facts:
        fact.numbers_verified = numbers_in(fact.value) <= known
        flagged += not fact.numbers_verified
    for flag in output.red_flags:
        flag.numbers_verified = numbers_in(f"{flag.title} {flag.explanation}") <= known
        flagged += not flag.numbers_verified
    return flagged
