import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))

from planted import PLANTED, found, recall


def test_found_matches_english_and_korean_wording():
    text = "The hourly wage is below the legal minimum. 임금은 현금 지급. No holiday pay."
    hits = found("parttime", text)
    assert hits["wage below minimum"] and hits["paid in cash"] and hits["no weekly rest day / holiday pay"]
    assert not hits["300,000 KRW deposit"]


def test_recall_is_a_share_of_the_planted_problems():
    assert recall("student", "nothing relevant here") == 0.0
    everything = "minimum wage; cash; school confirmation is empty; 33 hours; started working before the permit"
    assert recall("student", everything) == 1.0


def test_every_document_has_patterns_that_compile_and_are_not_trivially_true():
    for doc in PLANTED:
        assert not any(found(doc, "").values()), doc
