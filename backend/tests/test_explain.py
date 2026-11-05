import json

import pytest

from app.explain import DocType, LLMClient, classify, explain
from app.explain.parse import (
    ParseError,
    extract_json,
    locate_quote,
    numbers_in,
    parse_output,
    quote_in_text,
    verify_numbers,
    verify_quotes,
)
from app.explain.prompts import LANGUAGE_NAMES, build_prompt
from app.explain.schemas import DISCLAIMER, LLMOutput

GOOD = {
    "summary": "A monthly rent contract.",
    "key_facts": [
        {"label": "Deposit", "value": "5,000,000 KRW", "original_text": "보증금 금 5,000,000원정"}
    ],
    "red_flags": [
        {
            "title": "Broker fee on early exit",
            "explanation": "You pay the broker if you leave early.",
            "original_text": "만기전 이사시는 새임차인구하고 중개수수료를 임차인이 부담한다",
            "severity": "high",
        }
    ],
    "todos": [{"action": "Register your address", "deadline": "within 1 month"}],
}
SOURCE = "보증금 금5,000,000원정 ... 계약금은 위약금이되고 만기전이사시는새임차인구하고 중개수수료를임차인이부담한다"


# ---------- JSON extraction / parsing ----------
def test_extract_plain_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_surrounding_prose():
    assert extract_json('Sure! Here it is: {"a": {"b": 2}} Hope it helps') == {"a": {"b": 2}}


@pytest.mark.parametrize("raw", ["", "no json here", "[1, 2]", '{"a": '])
def test_extract_rejects_bad_input(raw):
    with pytest.raises(ParseError):
        extract_json(raw)


def test_parse_valid_output():
    out = parse_output(json.dumps(GOOD))
    assert out.red_flags[0].severity.value == "high"
    assert out.key_facts[0].quote_verified is False  # not verified until verify_quotes runs


def test_parse_missing_summary_is_reported():
    with pytest.raises(ParseError, match="summary"):
        parse_output(json.dumps({"key_facts": []}))


def test_parse_bad_severity_is_reported():
    bad = {**GOOD, "red_flags": [{**GOOD["red_flags"][0], "severity": "catastrophic"}]}
    with pytest.raises(ParseError, match="severity"):
        parse_output(json.dumps(bad))


def test_optional_lists_default_empty():
    assert parse_output('{"summary": "x"}') == LLMOutput(summary="x")


# ---------- quote verification ----------
def test_quote_matches_ignoring_spaces():
    assert quote_in_text("보증금 금 5,000,000원정", SOURCE)


def test_quote_tolerates_small_ocr_errors():
    assert quote_in_text("만기전 이사시는 새임차인구하고 중개수수료를 임차인이 부담합니다", SOURCE)


def test_invented_quote_is_rejected():
    assert not quote_in_text("임차인은 반려동물을 키울 수 없다", SOURCE)


def test_empty_and_tiny_quotes_are_not_verified():
    assert not quote_in_text("", SOURCE)
    assert quote_in_text("원", "금 5원 정")  # exact hit is fine
    assert not quote_in_text("월세", "금 5원 정")  # < 6 chars: no fuzzy matching


def test_verify_quotes_marks_items_and_counts():
    out = parse_output(json.dumps(GOOD))
    out.red_flags[0].original_text = "완전히 지어낸 조항입니다 제발 믿지 마세요"
    assert verify_quotes(out, SOURCE) == 1
    assert out.key_facts[0].quote_verified is True
    assert out.red_flags[0].quote_verified is False


def test_null_quote_is_left_alone():
    out = parse_output('{"summary": "x", "key_facts": [{"label": "a", "value": "b"}]}')
    assert verify_quotes(out, SOURCE) == 0
    assert out.key_facts[0].original_text is None


# ---------- classifier ----------
def test_classifies_rental():
    t = "부동산 월세 계약서 임대인과 임차인은 보증금 및 차임을 지급한다 확정일자"
    assert classify(t)[0] == DocType.RENTAL


def test_classifies_part_time_korean_and_english():
    assert classify("단시간근로자 표준근로계약서 시급 근로시간 주휴일 임금지급일")[0] == DocType.PART_TIME
    assert classify("Part-time work confirmation. Hourly wage, employer, work permit")[0] == DocType.PART_TIME


def test_classifies_english_phone_plan():
    t = "LG Youth Plan 31GB 5G unlimited calls SIM card fee number portability hotspot early termination"
    assert classify(t)[0] == DocType.PHONE_PLAN


def test_classifies_text_with_dropped_spaces():
    assert classify("임 대 차 계 약 서 임 대 인 임 차 인 보 증 금 월 세")[0] == DocType.RENTAL


@pytest.mark.parametrize("text", ["", "hello world", "오늘 저녁 메뉴는 김치찌개입니다", "Invoice #12 total 40 USD"])
def test_non_documents_are_unsupported(text):
    assert classify(text)[0] == DocType.UNSUPPORTED


# ---------- prompts ----------
@pytest.mark.parametrize("doc_type", [DocType.RENTAL, DocType.PHONE_PLAN, DocType.PART_TIME])
@pytest.mark.parametrize("lang", ["uz", "ru", "en"])
def test_prompts_build_for_every_type_and_language(doc_type, lang):
    system, user = build_prompt(doc_type, lang, "텍스트")
    assert LANGUAGE_NAMES[lang] in system
    assert "VERBATIM" in system and '"red_flags"' in system
    assert "텍스트" in user and "{language}" not in system


def test_no_prompt_for_unsupported():
    with pytest.raises(ValueError):
        build_prompt(DocType.UNSUPPORTED, "en", "x")


# ---------- service with a fake LLM ----------
class FakeLLM(LLMClient):
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def generate(self, system, messages, json_schema=None):
        self.calls.append(messages)
        return self.replies.pop(0)


def test_explain_happy_path():
    llm = FakeLLM([json.dumps(GOOD)])
    res = explain(SOURCE, DocType.RENTAL, "uz", llm, ocr_confidence=0.93, clause_review=False, translate=False)
    assert res.disclaimer == DISCLAIMER["uz"] and res.language == "uz"
    assert res.doc_type == DocType.RENTAL
    assert all(f.quote_verified for f in res.key_facts + res.red_flags)
    assert res.warnings == [] and len(llm.calls) == 1


def test_explain_retries_once_with_the_error_message():
    llm = FakeLLM(["not json at all", json.dumps(GOOD)])
    res = explain(SOURCE, DocType.RENTAL, "en", llm, clause_review=False, translate=False)
    assert res.summary and len(llm.calls) == 2
    retry_messages = llm.calls[1]
    assert [r for r, _ in retry_messages] == ["user", "model", "user"]
    assert "No JSON object" in retry_messages[-1][1]


def test_explain_gives_up_after_second_bad_reply():
    with pytest.raises(ParseError):
        explain(SOURCE, DocType.RENTAL, "en", FakeLLM(["bad", "still bad"]), clause_review=False, translate=False)


def test_explain_warns_about_hallucinated_quotes_and_low_ocr_confidence():
    bad = {**GOOD, "red_flags": [{**GOOD["red_flags"][0], "original_text": "존재하지 않는 조항 문장입니다 정말로"}]}
    res = explain(SOURCE, DocType.RENTAL, "en", FakeLLM([json.dumps(bad)]), ocr_confidence=0.6, clause_review=False, translate=False)
    assert len(res.warnings) == 2
    assert res.red_flags[0].quote_verified is False


# ---------- number verification ----------
def test_numbers_in_ignores_thousands_separators():
    assert numbers_in("5,000,000원 and 450,000 won, 12 months, 1.5%") == {"5000000", "450000", "12", "1.5"}
    assert numbers_in("no digits") == set()


def test_wrong_number_in_value_is_flagged():
    """Real failure seen with the local model: quote says 7700 won, value said 8,000 KRW."""
    source = "SIM card fee: 7700 won (one-time deduction)"
    out = parse_output(json.dumps({
        "summary": "x",
        "key_facts": [
            {"label": "SIM fee", "value": "8,000 KRW", "original_text": "SIM card fee: 7700 won"},
            {"label": "SIM fee ok", "value": "7,700 KRW"},
        ],
    }))
    assert verify_numbers(out, source) == 1
    assert out.key_facts[0].numbers_verified is False
    assert out.key_facts[1].numbers_verified is True


def test_red_flag_with_invented_number_is_flagged():
    out = parse_output(json.dumps({
        "summary": "x",
        "red_flags": [{"title": "Penalty", "explanation": "You pay 300,000 won if you leave", "severity": "high"}],
    }))
    assert verify_numbers(out, "penalty applies") == 1
    assert out.red_flags[0].numbers_verified is False


def test_explain_warns_when_a_number_is_not_in_the_scan():
    wrong = {**GOOD, "key_facts": [{"label": "Deposit", "value": "9,999,999 KRW"}]}
    res = explain(SOURCE, DocType.RENTAL, "en", FakeLLM([json.dumps(wrong)]), clause_review=False, translate=False)
    assert res.key_facts[0].numbers_verified is False
    assert any("number" in w for w in res.warnings)

# ---------- quote snapping ----------
def test_locate_quote_returns_scan_text_not_the_models_version():
    scan = "제1조 보증금\n금5,000,000원정\n계약금 금 500,000원정"
    found = locate_quote("보증금 5,000,000원", scan)
    assert found is not None and found in scan and "5,000,000" in found


def test_verify_quotes_snaps_to_scan_text():
    scan = "보증금\n금5,000,000원정 은 계약시에 지급한다"
    out = parse_output(json.dumps({"summary": "x", "key_facts": [
        {"label": "Deposit", "value": "5,000,000", "original_text": "보증금 5,000,000원"}]}))
    assert verify_quotes(out, scan) == 0
    fact = out.key_facts[0]
    assert fact.quote_verified and fact.original_text in scan
    assert fact.original_text != "보증금 5,000,000원"


def test_locate_quote_none_for_invented_text():
    assert locate_quote("전혀 없는 문장을 지어냈습니다", "보증금 금5,000,000원정") is None
