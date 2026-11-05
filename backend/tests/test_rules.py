from app.explain.rules import merge_flags, part_time_flags, rule_flags
from app.explain.schemas import DocType, RedFlag, Severity

CONTRACT = """표준근로계약서 (단시간근로자)
1. 근로개시일 : 2026년 9월 1일부터 2027년 2월 28일까지
5. 근무일/휴일 : 매주 월, 화, 수, 목, 금요일 근무 / 주휴일 : 없음
- 시간급 : 9,000원
- 임금지급일 : 매월 말일 / 지급방법 : 현금으로 직접 지급
8. 사회보험 적용여부 : 고용보험 [ ] 산재보험 [ ] 국민연금 [ ] 건강보험 [ ] (가입하지 않음)
"""

STUDENT = """시간제취업 확인서
근무요일 및 시간 : 월~금 18:00 ~ 23:00, 토 10:00 ~ 18:00 (주 33시간)
시급 : 9,500원      임금지급방법 : 현금
학교 유학생 담당자 확인 : (미기재)
"""


def titles(flags):
    return [f.title for f in flags]


def test_wage_below_minimum_is_high_and_quotes_the_line():
    flags = part_time_flags(CONTRACT)
    wage = next(f for f in flags if f.title == "Hourly wage below the legal minimum")
    assert wage.severity == Severity.HIGH
    assert "9,000" in wage.explanation and "10,320" in wage.explanation
    assert wage.original_text in CONTRACT


def test_wage_between_the_two_years_is_a_warning_for_next_year():
    text = "계약기간 2026년 9월 1일부터 2027년 2월 28일까지\n시급 : 10,500원"
    flags = part_time_flags(text)
    assert titles(flags) == ["Wage will fall below the minimum next year"]
    assert flags[0].severity == Severity.MEDIUM and "10,700" in flags[0].explanation


def test_wage_at_or_above_minimum_is_not_flagged():
    assert part_time_flags("계약기간 2026년 3월\n시급 : 10,320원") == []
    assert part_time_flags("계약기간 2027년 3월\n시급 : 10,700원") == []


def test_rest_day_insurance_and_cash():
    t = titles(part_time_flags(CONTRACT))
    assert "No weekly rest day or holiday pay" in t
    assert "No social insurance" in t
    assert "Paid in cash" in t


def test_student_form_hours_and_blank_fields():
    flags = part_time_flags(STUDENT)
    by_title = {f.title: f for f in flags}
    assert by_title["Weekly hours are above what a student may work"].severity == Severity.HIGH
    assert by_title["A required field is empty"].severity == Severity.HIGH
    assert "Hourly wage below the legal minimum" in by_title


def test_no_overtime_pay():
    flags = part_time_flags("- 연장·야간근로수당 : 지급하지 않음 (포괄하여 시급에 포함됨)")
    assert titles(flags) == ["No overtime or night pay"]
    assert part_time_flags("- 연장근로수당 : 통상임금의 50% 가산 지급") == []


def test_no_copy_of_contract_and_work_before_permit():
    copy = part_time_flags("9. 근로계약서 교부 : 본 계약서는 사업주가 보관하며 근로자에게 교부하지 않는다.")
    assert titles(copy) == ["You do not get a copy of the contract"]
    started = part_time_flags("시간제취업 확인서\n근무는 2026년 9월 1일부터 시작하였습니다.")
    assert titles(started) == ["Work started before the permit"]
    # the "already started" rule is for student forms only
    assert part_time_flags("영업은 2026년 9월 1일부터 시작하였습니다.") == []


def test_weekly_hours_only_checked_on_student_forms():
    assert part_time_flags("근무시간은 주 33시간 이다") == []


def test_other_document_types_have_no_rules():
    assert rule_flags(DocType.RENTAL, CONTRACT) == []


def test_merge_drops_model_flags_about_the_same_line():
    rule = part_time_flags(CONTRACT)
    same = RedFlag(title="Wage", explanation="x", severity=Severity.LOW,
                   original_text="6. 임금 - 시간급 : 9,000원 - 상여금 : 없음", quote_verified=True)
    other = RedFlag(title="Other", explanation="y", severity=Severity.LOW,
                    original_text="전혀 다른 조항입니다", quote_verified=True)
    merged = merge_flags(rule, [same, other])
    assert "Other" in titles(merged) and "Wage" not in titles(merged)
    assert merged[: len(rule)] == rule


# ---------- blank forms ----------
BLANK = """보증금:                원, 차임: 월              원
계약 기간:    .    .    . ~     .    .    .
임대인 (        ) 임차인 (        )
2026 년     월     일
성명 ________ 주소 ________
"""


def test_blank_form_is_detected_and_filled_contract_is_not():
    from app.explain.rules import looks_blank

    assert looks_blank(BLANK)
    assert not looks_blank(CONTRACT)
    assert not looks_blank("보증금 5,000,000원 월세 450,000원 계약기간 2026.06.15 ~ 2028.06.15")
