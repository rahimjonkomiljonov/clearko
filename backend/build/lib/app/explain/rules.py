"""Objective checks that do not need a language model.

A 7B model reads "시간급 : 9,000원" as a plain fact and misses that it is below the minimum
wage. These rules look for a few clear patterns in part-time documents and write the red flag
themselves. The quote is the scan's own line, so it is verbatim by construction.
"""

from __future__ import annotations

import re

from .prompts import MIN_WAGE_KRW
from .schemas import DocType, RedFlag, Severity

_WAGE = re.compile(r"(시간급|시급|시간당)[^0-9\n]{0,8}([0-9][0-9,]{3,6})\s*원")
_WEEKLY_HOURS = re.compile(r"주\s*([0-9]{1,2})\s*시간")
_YEAR = re.compile(r"(20[0-9]{2})\s*년")
_NO_REST_DAY = re.compile(r"주휴일[^\n]{0,6}(없음|없다|해당\s*없)")
_NOT_INSURED = re.compile(r"(보험|연금)[^\n]{0,40}가입(하지\s*않|안\s*함|안함)")
_CASH = re.compile(r"현금")
_BLANK = re.compile(r"\(\s*미기재\s*\)|미기재")
_NO_OVERTIME_PAY = re.compile(r"(연장|야간|휴일)[^\n]{0,12}수당[^\n]{0,10}(지급\s*하지\s*않|없음|지급\s*안)")
_WORKER_DEPOSIT = re.compile(r"(보증금|예치금)")
_DEDUCT_COSTS = re.compile(r"(유니폼|파손|손해|물품|비용)[^\n]*공제")
_NO_COPY =re.compile(r"교부\s*하지\s*않|교부\s*안\s*함|교부\s*하지\s*아니")
_ALREADY_WORKING = re.compile(r"시작\s*하였|시작\s*했|이미\s*근무")

STUDENT_HOURS_HIGH = 30  # no student permit allows more
STUDENT_HOURS_CHECK = 20  # the usual limit for undergraduates who meet the language requirement


# Empty fill-in slots as they appear in the text layer of a blank form.
_EMPTY_SLOTS = [
    re.compile(r"(?<![0-9,])[ \t]{4,}원"),  # "보증금:            원"
    re.compile(r"_{4,}"),  # "______"
    re.compile(r"\([ \t]{4,}\)"),  # "(        )"
    re.compile(r"년[ \t]{3,}월[ \t]{3,}일"),  # empty date
    re.compile(r"\.[ \t]{3,}\.[ \t]{3,}\."),  # ".    .    ."
]
BLANK_FORM_MIN_SLOTS = 6


def looks_blank(text: str) -> bool:
    """True for an unfilled form (a template): it has many empty slots to fill in.

    A photo of a blank form is not detected (OCR does not keep the wide spaces); that is fine.
    """
    return sum(len(p.findall(text)) for p in _EMPTY_SLOTS) >= BLANK_FORM_MIN_SLOTS


def _flag(title: str, why: str, line: str, severity: Severity) -> RedFlag:
    return RedFlag(title=title, explanation=why, original_text=line.strip(),
                   quote_verified=True, severity=severity)


def _years(text: str) -> list[int]:
    return sorted({int(y) for y in _YEAR.findall(text) if int(y) in MIN_WAGE_KRW})


def _wage_flag(line: str, years: list[int]) -> RedFlag | None:
    m = _WAGE.search(line)
    if not m:
        return None
    wage = int(m.group(2).replace(",", ""))
    first = years[0] if years else max(MIN_WAGE_KRW)
    if wage < MIN_WAGE_KRW[first]:
        return _flag(
            "Hourly wage below the legal minimum",
            f"The hourly wage is {wage:,} KRW. The legal minimum wage is {MIN_WAGE_KRW[first]:,} KRW "
            f"per hour in {first}. Paying less is not allowed, even if you agree to it. "
            "Ask for a correction or contact the Ministry of Employment and Labor (call 1350).",
            line, Severity.HIGH,
        )
    later = [y for y in years if y > first and wage < MIN_WAGE_KRW[y]]
    if later:
        y = later[0]
        return _flag(
            "Wage will fall below the minimum next year",
            f"The hourly wage is {wage:,} KRW. From 1 January {y} the legal minimum is "
            f"{MIN_WAGE_KRW[y]:,} KRW per hour, so this wage is too low for the part of the "
            f"contract in {y}.",
            line, Severity.MEDIUM,
        )
    return None


def part_time_flags(text: str) -> list[RedFlag]:
    """Red flags for labor contracts and student work confirmations."""
    years = _years(text)
    student_form = "시간제취업" in re.sub(r"\s+", "", text)
    flags: list[RedFlag] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if (w := _wage_flag(line, years)) is not None:
            flags.append(w)
        if _NO_REST_DAY.search(line):
            flags.append(_flag(
                "No weekly rest day or holiday pay",
                "The contract says there is no weekly rest day (주휴일). Workers who work 15 hours "
                "or more per week are entitled to a paid weekly rest day (주휴수당).",
                line, Severity.HIGH))
        if _NOT_INSURED.search(line):
            flags.append(_flag(
                "No social insurance",
                "The employer does not enrol the worker in social insurance (national pension, "
                "health, employment, accident). Employers must do this for most workers, and "
                "missing insurance can also cause problems with your visa and health care.",
                line, Severity.HIGH))
        if _CASH.search(line) and re.search(r"지급|급여|임금|지불", line):
            flags.append(_flag(
                "Paid in cash",
                "Cash payment leaves no record. Ask for a payslip or a bank transfer, because "
                "you need proof of income and of the hours you worked.",
                line, Severity.MEDIUM))
        if student_form and (h := _WEEKLY_HOURS.search(line)):
            hours = int(h.group(1))
            if hours > STUDENT_HOURS_HIGH:
                flags.append(_flag(
                    "Weekly hours are above what a student may work",
                    f"The form says {hours} hours per week. No student permit allows more than "
                    f"{STUDENT_HOURS_HIGH} hours, and most students may work 10 to 20 hours. "
                    "Working above the permitted hours can lead to a fine, a visa problem and "
                    "trouble for the employer.",
                    line, Severity.HIGH))
            elif hours > STUDENT_HOURS_CHECK:
                flags.append(_flag(
                    "Check the weekly hour limit",
                    f"The form says {hours} hours per week. Many students may work only 10 to "
                    f"{STUDENT_HOURS_CHECK} hours. Check the limit for your school and Korean "
                    "level with your international office before you start.",
                    line, Severity.MEDIUM))
        if _NO_OVERTIME_PAY.search(line):
            flags.append(_flag(
                "No overtime or night pay",
                "The contract says overtime, night or holiday work is not paid extra. The law "
                "requires 50% extra pay for overtime, night work (22:00 to 06:00) and holiday "
                "work at workplaces with 5 or more employees. Saying it is 'included' in the "
                "hourly wage is not valid unless the wage clearly covers it.",
                line, Severity.MEDIUM))
        if _WORKER_DEPOSIT.search(line) and re.search(r"근로자|입사|맡기", line):
            flags.append(_flag(
                "The employer holds a deposit from you",
                "The employer asks you to leave a deposit and decides alone whether to return it. "
                "Employers generally may not take money from a worker as a guarantee or penalty "
                "(Labor Standards Act, articles 20 and 22). Do not hand over cash without a "
                "receipt, and ask a labor office (1350) before you agree.",
                line, Severity.HIGH))
        if _DEDUCT_COSTS.search(line) and "근로자" in line:
            flags.append(_flag(
                "Costs are taken out of your wages",
                "The contract lets the employer deduct the cost of a uniform or broken items from "
                "your wages. Wages must generally be paid in full (Labor Standards Act, article "
                "43), so such deductions are usually not allowed. Ask for it to be removed.",
                line, Severity.MEDIUM))
        if _NO_COPY.search(line):
            flags.append(_flag(
                "You do not get a copy of the contract",
                "The employer must give you a copy of the signed contract (Labor Standards Act, "
                "article 17). Without a copy you cannot prove the wage, hours or duties. Ask for "
                "a signed copy, or take a photo of every page before you leave.",
                line, Severity.HIGH))
        if student_form and _ALREADY_WORKING.search(line):
            flags.append(_flag(
                "Work started before the permit",
                "The form says work has already started. A student must receive the part-time "
                "work permit BEFORE starting. Working earlier can be punished, for the student "
                "(visa problems, fine) and for the employer. Stop and check with your school.",
                line, Severity.HIGH))
        if student_form and _BLANK.search(line):
            flags.append(_flag(
                "A required field is empty",
                "This part of the form is marked as not filled in. The school confirmation and "
                "the immigration permit must be complete BEFORE you start work. Working without "
                "the permit can be punished, for the student and the employer.",
                line, Severity.HIGH))
    return _unique(flags)


def _unique(flags: list[RedFlag]) -> list[RedFlag]:
    seen: set[tuple[str, str]] = set()
    out = []
    for f in flags:
        key = (f.title, f.original_text)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def rule_flags(doc_type: DocType, text: str) -> list[RedFlag]:
    if doc_type == DocType.PART_TIME:
        return part_time_flags(text)
    return []


def merge_flags(rule: list[RedFlag], model: list[RedFlag]) -> list[RedFlag]:
    """Rule flags first. A model flag about the same text as a rule flag is dropped."""
    def squash(s: str) -> str:
        return re.sub(r"\s+", "", s)

    rule_lines = [squash(f.original_text) for f in rule]
    kept = [
        f for f in model
        if not any(line and (line in squash(f.original_text)) for line in rule_lines)
    ]
    return rule + kept
