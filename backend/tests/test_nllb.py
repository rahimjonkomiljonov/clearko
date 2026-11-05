"""NLLB wrapper: sentence splitting and joining. The real model is not loaded in these tests."""

from app.explain.nllb import NLLBTranslator, split_sentences
from app.explain.schemas import DocType, Explanation, KeyFact
from app.explain.translate import translate_explanation


def test_split_sentences_basic():
    text = "The tenant pays 5,000,000 KRW. The landlord keeps it. Rate is 1.5 percent."
    assert split_sentences(text) == [
        "The tenant pays 5,000,000 KRW.",
        "The landlord keeps it.",
        "Rate is 1.5 percent.",
    ]


def test_split_sentences_keeps_single_sentence_and_empty():
    assert split_sentences("Monthly Rent") == ["Monthly Rent"]
    assert split_sentences("   ") == []


class FakeNLLB(NLLBTranslator):
    """Replaces the model with 'UZ:' + text so we can test the split/join logic."""

    def __init__(self):
        super().__init__()
        self.seen: list[str] = []

    def _run(self, target_code, sentences):
        self.seen += sentences
        return [f"UZ:{s}" for s in sentences]


def test_each_sentence_is_translated_separately_and_rejoined():
    tr = FakeNLLB()
    out = tr("uz", ["One. Two.", "Three"])
    assert tr.seen == ["One.", "Two.", "Three"]
    assert out == ["UZ:One. UZ:Two.", "UZ:Three"]


def test_unknown_language_returns_none():
    assert FakeNLLB()("xx", ["Hello"]) is None


def test_works_as_explanation_translator_with_number_check():
    exp = Explanation(
        summary="Rent is 450,000 KRW.",
        key_facts=[KeyFact(label="Rent", value="450,000 KRW")],
        red_flags=[], todos=[],
        doc_type=DocType.RENTAL, language="uz", disclaimer="x",
    )

    class SpacedNumbers(FakeNLLB):
        def _run(self, target_code, sentences):
            return [s.replace("450,000", "450 000") for s in sentences]

    exp, kept = translate_explanation(exp, "uz", SpacedNumbers())
    assert kept == 0  # "450 000" and "450,000" are the same number
    assert "450 000" in exp.summary

    class WrongNumber(FakeNLLB):
        def _run(self, target_code, sentences):
            return [s.replace("450,000", "540,000") for s in sentences]

    exp2 = Explanation(
        summary="Rent is 450,000 KRW.", key_facts=[], red_flags=[], todos=[],
        doc_type=DocType.RENTAL, language="uz", disclaimer="x",
    )
    exp2, kept2 = translate_explanation(exp2, "uz", WrongNumber())
    assert kept2 == 1 and exp2.summary == "Rent is 450,000 KRW."
