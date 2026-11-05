import json
import re

from app.explain import DocType, LLMClient, explain
from app.explain.clauses import batch_clauses, split_clauses
from app.explain.judge import judge_clauses
from app.explain.schemas import Explanation, KeyFact, RedFlag, Severity, Todo
from app.explain.translate import translate_explanation

CONTRACT = """--- page 1 ---
부동산(다가구주택)월세 계약서
제1조[목적]위 부동산의 임대차에 한하여 임대인과 임차인은 합의에 의하여 보증금을 지급하기로 한다
보증금 금5,000,000원정
제5조[계약의 종료]임대차 계약이 종료된 경우 임차인은 부동산을 원상으로 회복하여 반환한다
[특약사항]
거래당사자는 개인정보 제공및 이용에 동의한다
계약금은 위약금이되고 만기전 이사시는 새임차인구하고 중개수수료를 임차인이 부담한다
집을깨끗히사용한다 지저분하게사용하면 이사갈시에 청소비 부담한다
본 계약을 증명하기 위하여 계약 당사자가 이의 없음을 확인하고
성명 임대인
"""


def clause_ids_in(user_prompt: str) -> list[int]:
    return [int(x) for x in re.findall(r"^\[(\d+)\]", user_prompt, flags=re.MULTILINE)]


class RoutingLLM(LLMClient):
    """Answers each kind of request the way a well-behaved model would."""

    def __init__(self, high_phrase="중개수수료", drop_ids=(), garble_translation=False):
        self.high_phrase, self.drop_ids, self.garble = high_phrase, set(drop_ids), garble_translation
        self.calls = {"overview": 0, "judge": 0, "translate": 0}

    def generate(self, system, messages, json_schema=None):
        user = messages[0][1]
        if "Translate every string" in system:
            self.calls["translate"] += 1
            strings = json.loads(user)["strings"]
            out = [f"UZ:{s}" for s in strings]
            if self.garble:
                out = [s.replace("5,000,000", "5,500,000") for s in out]
            return json.dumps({"strings": out})
        if user.startswith("CLAUSES:"):
            self.calls["judge"] += 1
            items = []
            for line in user.splitlines()[1:]:
                m = re.match(r"\[(\d+)\]", line)
                if not m:
                    continue
                cid = int(m.group(1))
                if cid in self.drop_ids:
                    continue
                bad = self.high_phrase in line
                items.append({"id": cid, "title": "Broker fee" if bad else "Standard",
                              "meaning": "Something.", "concern": "high" if bad else "none",
                              "why": "You pay when leaving." if bad else ""})
            return json.dumps({"items": items})
        self.calls["overview"] += 1
        return json.dumps({"summary": "A rental contract.", "red_flags": [],
                           "key_facts": [{"label": "Deposit", "value": "5,000,000 KRW",
                                          "original_text": "보증금 5,000,000원"}],
                           "todos": [{"action": "Register address", "deadline": None}]})


# ---------- splitting ----------
def test_special_terms_are_split_one_per_line_and_stop_at_signature_block():
    texts = [c.text for c in split_clauses(CONTRACT)]
    assert any(t.startswith("계약금은 위약금") for t in texts)
    assert any(t.startswith("집을깨끗히") for t in texts)
    assert not any("성명 임대인" in t for t in texts)


def test_articles_start_new_clauses_and_page_markers_are_dropped():
    clauses = split_clauses(CONTRACT)
    assert any(c.text.startswith("제1조") for c in clauses)
    assert any(c.text.startswith("제5조") for c in clauses)
    assert all("--- page" not in c.text for c in clauses)


def test_ids_are_sequential_and_crumbs_are_dropped():
    clauses = split_clauses("A\n12\n---\n제1조 이것은 충분히 긴 조항의 내용입니다 정말로\n")
    assert [c.id for c in clauses] == list(range(1, len(clauses) + 1))
    assert len(clauses) == 1


def test_english_numbered_points_are_separate_clauses():
    text = "(1) This plan requires a 12-month contract and a penalty applies.\n(2) The plan cannot be cancelled during the first 95 days."
    assert len(split_clauses(text)) == 2


def test_batching_respects_limits():
    clauses = split_clauses("\n".join(f"(1) clause number {i} " + "x" * 200 for i in range(12)))
    batches = batch_clauses(clauses, max_chars=700, max_items=10)
    assert all(len(b) <= 10 and sum(len(c.text) for c in b) <= 700 + 260 for b in batches)
    assert sum(len(b) for b in batches) == len(clauses)


# ---------- judge ----------
def test_judge_flags_only_concerning_clauses_with_verbatim_quote():
    clauses = split_clauses(CONTRACT)
    flags, unanswered = judge_clauses(RoutingLLM(), DocType.RENTAL, clauses)
    assert unanswered == [] and len(flags) == 1
    assert flags[0].severity == Severity.HIGH and flags[0].quote_verified
    assert flags[0].original_text in " ".join(c.text for c in clauses)


def reviewed(clauses):
    return [c for c in clauses if c.kind not in ("article", "notice")]


def test_judge_retries_unanswered_clauses_then_reports_leftovers():
    clauses = split_clauses(CONTRACT)
    first_id = reviewed(clauses)[0].id
    _, unanswered = judge_clauses(RoutingLLM(drop_ids=[first_id]), DocType.RENTAL, clauses)
    assert unanswered == [first_id]  # model never answers it, even on retry


def test_judge_survives_garbage_replies():
    class Garbage(LLMClient):
        def generate(self, system, messages, json_schema=None):
            return "I cannot do that"

    clauses = split_clauses(CONTRACT)
    flags, unanswered = judge_clauses(Garbage(), DocType.RENTAL, clauses)
    assert flags == [] and len(unanswered) == len(reviewed(clauses))


def test_clauses_are_tagged_article_special_or_other():
    def kind_of(prefix: str) -> str:
        return next(c.kind for c in split_clauses(CONTRACT) if c.text.startswith(prefix))

    assert kind_of("제1조") == "article" and kind_of("제5조") == "article"
    assert kind_of("계약금은 위약") == "special" and kind_of("집을깨끗히") == "special"


def test_without_a_special_terms_section_nothing_is_called_an_article():
    text = "제1조 이것은 충분히 긴 조항의 내용입니다 정말로\n제2조 이것도 충분히 긴 조항의 내용입니다 정말로"
    assert {c.kind for c in split_clauses(text)} == {"other"}


def test_printed_articles_are_not_sent_to_the_model():
    seen: list[str] = []

    class Spy(RoutingLLM):
        def generate(self, system, messages, json_schema=None):
            seen.append(messages[0][1])
            return super().generate(system, messages, json_schema)

    judge_clauses(Spy(), DocType.RENTAL, split_clauses(CONTRACT))
    sent = "\n".join(seen)
    assert "제1조" not in sent and "계약금은 위약금" in sent


def test_severity_floor_raises_but_never_lowers():
    from app.explain.judge import _apply_floor

    broker = "계약금은 위약금이되고 만기전이사시는 새임차인구하고 중개수수료를 임차인이 부담한다"
    assert _apply_floor(Severity.LOW, broker) == Severity.HIGH
    assert _apply_floor(Severity.HIGH, "집을 깨끗이 사용한다 청소비 부담한다") == Severity.HIGH
    assert _apply_floor(Severity.LOW, "집을 깨끗이 사용한다 청소비 부담한다") == Severity.LOW
    assert _apply_floor(Severity.LOW, "민원들어오면 퇴거시키고") == Severity.HIGH
    assert _apply_floor(Severity.LOW, "위약금은 계약금으로 한다") == Severity.MEDIUM


# ---------- translation ----------
def make_exp():
    return Explanation(
        summary="Deposit is 5,000,000 KRW.", language="uz", doc_type=DocType.RENTAL, disclaimer="d",
        key_facts=[KeyFact(label="Deposit", value="5,000,000 KRW", original_text="보증금")],
        red_flags=[RedFlag(title="Broker fee", explanation="You pay 12 months.", severity=Severity.HIGH)],
        todos=[Todo(action="Register", deadline="within 30 days")],
    )


def test_translation_replaces_text_but_keeps_korean_quotes():
    exp, kept = translate_explanation(make_exp(), "uz", RoutingLLM())
    assert kept == 0 and exp.summary.startswith("UZ:")
    assert exp.key_facts[0].original_text == "보증금"
    assert exp.todos[0].deadline.startswith("UZ:")


def test_translation_with_changed_number_is_rejected_per_string():
    exp, kept = translate_explanation(make_exp(), "uz", RoutingLLM(garble_translation=True))
    assert kept == 2  # summary and key-fact value had the number altered
    assert exp.summary == "Deposit is 5,000,000 KRW."
    assert exp.red_flags[0].title.startswith("UZ:")


def test_translation_failure_keeps_english():
    class Broken(LLMClient):
        def generate(self, system, messages, json_schema=None):
            return "no"

    exp, kept = translate_explanation(make_exp(), "ru", Broken())
    assert kept > 0 and exp.summary == "Deposit is 5,000,000 KRW."


# ---------- full flow ----------
def test_explain_full_flow_in_uzbek():
    llm = RoutingLLM()
    res = explain(CONTRACT, DocType.RENTAL, "uz", llm, ocr_confidence=0.95)
    assert llm.calls["overview"] == 1 and llm.calls["judge"] >= 1 and llm.calls["translate"] >= 1
    assert res.language == "uz" and "tushunishingizga" in res.disclaimer
    assert len(res.red_flags) == 1 and res.red_flags[0].title.startswith("UZ:")
    assert "중개수수료" in res.red_flags[0].original_text  # Korean stays Korean
    assert res.key_facts[0].quote_verified


def test_english_skips_translation():
    llm = RoutingLLM()
    explain(CONTRACT, DocType.RENTAL, "en", llm)
    assert llm.calls["translate"] == 0


def test_unreviewed_clauses_produce_a_warning():
    clauses = split_clauses(CONTRACT)
    res = explain(CONTRACT, DocType.RENTAL, "en", RoutingLLM(drop_ids=[reviewed(clauses)[0].id]))
    assert any("could not be reviewed" in w for w in res.warnings)


def test_high_severity_flags_sort_first():
    llm = RoutingLLM(high_phrase="청소비")  # a later clause is the "high" one
    res = explain(CONTRACT, DocType.RENTAL, "en", llm)
    assert res.red_flags[0].severity == Severity.HIGH


def test_judge_rejects_chinese_answers_and_retries():
    class DriftsOnce(LLMClient):
        def __init__(self):
            self.n = 0

        def generate(self, system, messages, json_schema=None):
            self.n += 1
            ids = clause_ids_in(messages[0][1].replace("CLAUSES:", "").strip())
            text = "定金作为违约金" if self.n == 1 else "A deposit penalty."
            return json.dumps({"items": [{"id": i, "title": "t", "meaning": text, "concern": "medium", "why": text} for i in ids]})

    clauses = split_clauses(CONTRACT)
    flags, unanswered = judge_clauses(DriftsOnce(), DocType.RENTAL, clauses)
    assert unanswered == [] and flags
    assert all("违" not in f.explanation for f in flags)
