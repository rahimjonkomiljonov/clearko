"""Translate an English explanation into the user's language, with a number check."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel

from .llm_client import LLMClient
from .parse import ParseError, extract_json, numbers_in
from .prompts import build_translate_prompt
from .schemas import Explanation

BATCH = 8  # small models drop or merge items in longer lists


class StringTranslator(Protocol):
    """Translates English strings into `lang`. Returns None when it could not (keep English)."""

    def __call__(self, lang: str, strings: list[str]) -> list[str] | None: ...


class _Strings(BaseModel):
    strings: list[str]


def _translate_batch(client: LLMClient, lang: str, strings: list[str]) -> list[str] | None:
    system, user = build_translate_prompt(lang, strings)
    schema = _Strings.model_json_schema()
    for _ in range(2):
        try:
            raw = client.generate(system, [("user", user)], schema)
            out = _Strings.model_validate(extract_json(raw))
        except (ParseError, ValueError):
            continue
        if len(out.strings) == len(strings):
            return out.strings
    return None


def llm_translator(client: LLMClient) -> StringTranslator:
    """Translate with a chat model (works well for Russian, not for Uzbek)."""
    return lambda lang, strings: _translate_batch(client, lang, strings)


def translate_explanation(
    exp: Explanation,
    lang: str,
    translator: LLMClient | StringTranslator,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[Explanation, int]:
    """Translate in place. Returns (explanation, number of strings left in English).

    `translator` is a chat-model client or a StringTranslator (e.g. NLLB). A translated string is
    accepted only if it contains exactly the same numbers as the English one; otherwise the
    English text is kept (a wrong number is worse than the wrong language).
    """
    translate = llm_translator(translator) if hasattr(translator, "generate") else translator
    setters: list[tuple[str, Callable[[str], None]]] = []

    def add(value: str, setter: Callable[[str], None]) -> None:
        if value.strip():
            setters.append((value, setter))

    add(exp.summary, lambda v: setattr(exp, "summary", v))
    for f in exp.key_facts:
        add(f.label, lambda v, f=f: setattr(f, "label", v))
        add(f.value, lambda v, f=f: setattr(f, "value", v))
    for r in exp.red_flags:
        add(r.title, lambda v, r=r: setattr(r, "title", v))
        add(r.explanation, lambda v, r=r: setattr(r, "explanation", v))
    for t in exp.todos:
        add(t.action, lambda v, t=t: setattr(t, "action", v))
        if t.deadline:
            add(t.deadline, lambda v, t=t: setattr(t, "deadline", v))

    kept_english = 0
    chunks = [setters[i : i + BATCH] for i in range(0, len(setters), BATCH)]
    for n, chunk in enumerate(chunks, 1):
        translated = translate(lang, [s for s, _ in chunk])  # type: ignore[operator]
        for i, (original, setter) in enumerate(chunk):
            if translated is not None and numbers_in(translated[i]) == numbers_in(original):
                setter(translated[i])
            else:
                kept_english += 1
        if on_progress:
            on_progress(n, len(chunks))
    return exp, kept_english
