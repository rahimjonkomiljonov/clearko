"""One prompt template per document type. All return the same JSON shape."""

from __future__ import annotations

from .schemas import DocType

LANGUAGE_NAMES = {
    "uz": "Uzbek (Latin script, simple everyday words)",
    "ru": "Russian (simple everyday words)",
    "en": "English (simple everyday words, B1 level)",
}

# Facts the prompts rely on. VERIFY these against official sources before each release.
MIN_WAGE_2026_KRW = 10_320  # Korean statutory minimum hourly wage for 2026 (verify)

JSON_SHAPE = """\
Return ONLY a JSON object, no other text, in exactly this shape:
{
  "summary": "3-5 plain sentences",
  "key_facts": [{"label": "...", "value": "...", "original_text": "verbatim Korean/source text or null"}],
  "red_flags": [{"title": "...", "explanation": "...", "original_text": "verbatim source text",
                 "severity": "low" | "medium" | "high"}],
  "todos": [{"action": "...", "deadline": "date/period or null"}]
}"""

BASE_RULES = """\
You help international students and workers in Korea understand documents. The user cannot read
Korean well. The text below comes from OCR of a photo, so it may contain spelling mistakes,
missing spaces, jumbled reading order and misread digits.

Rules:
1. Use ONLY the document text. Never invent amounts, dates or clauses. If something is not in the
   text, write "not found in the document" as the value. Do not guess.
2. Amounts and dates: copy the digits exactly as they appear. If a digit looks doubtful (OCR),
   say so in the value, for example "450,000 KRW (check the original: scan may be unclear)".
3. "original_text" must be copied VERBATIM from the document text (same Korean characters). Do not
   translate it and do not fix it. Use null if the fact is not from one specific passage.
4. Write every field EXCEPT original_text in {language}. Keep names, numbers and units clear.
5. A red flag is something unusual, one-sided or costly for the user. For each: say what it means
   in practice, and why it matters. Do not label ordinary standard clauses as red flags.
   Severity: high = could cost a lot of money or lose the home/job/number; medium = worth
   negotiating or checking; low = good to know.
6. You are not a lawyer. Do not say a clause is "illegal"; say it "may be a problem" and suggest
   checking with an official counter or lawyer when the issue is serious.
7. todos: concrete next steps with deadlines found in the text, or standard legal deadlines you
   are sure about. Otherwise leave deadline null.
8. If a text is clearly a form that has not been filled in, say so in the summary and explain what
   each section is for instead of inventing values.
"""

CHECKLISTS: dict[DocType, str] = {
    DocType.RENTAL: """\
Document type: Korean rental contract (월세/전세/원룸), possibly with attachments such as the
broker's property description (중개대상물 확인·설명서) and legal notices.
Look for and report as key_facts when present: deposit (보증금), monthly rent (차임/월세),
down payment (계약금), balance and its date (잔금), contract period and move-in date, maintenance
fee, who pays repair costs, how the deposit is returned, broker fee (중개보수) and who pays it.
Check for red flags such as: tenant pays broker fee when leaving early; deposit not returned or
returned late; cleaning or restoration charges that are open-ended; rules about visitors or
co-residents; eviction on complaints; penalties for leaving early; special terms (특약사항) that
shift repairs or utilities onto the tenant; missing 확정일자 / 전입신고 protection; the landlord's
account name not matching the landlord; mortgages or other rights on the property in the broker
sheet; basement or semi-basement (지하) risk such as flooding and mold.
Todos to consider: 전입신고 and 확정일자 (get the fixed date stamp) as soon as moving in,
rental report (임대차 신고) within 30 days if the deposit is over 60,000,000 KRW or the monthly
rent over 300,000 KRW, check the registry (등기부등본) before paying, keep payment receipts.
""",
    DocType.PHONE_PLAN: """\
Document type: mobile phone plan / subscription (may be a Korean form or an English or other
reseller flyer).
Report as key_facts when present: monthly price and what it includes (data, calls, texts), the
promotional price and how long it lasts, the price after the promotion, contract length,
cancellation or early termination penalty, device installment, fees (SIM, number portability,
activation), visa or ID requirements, age conditions, hotspot or speed limits.
Check for red flags such as: price rising sharply after a promotion; long lock-in period; vague
or unstated penalty amounts; no cancellation during an initial period; the number being cancelled
if the visa changes; conditions on bonuses (age, bundles); data throttling; auto-renewal.
Todos to consider: set a reminder before the promotion ends, check whether the plan can be
changed without losing the number, keep the contract copy, ask the amount of the penalty before
signing.
""",
    DocType.PART_TIME: f"""\
Document type: part-time job document in Korea: a labor contract (표준근로계약서 / 단시간근로자)
or a student part-time work confirmation (시간제취업 확인서) for foreign students.
Report as key_facts when present: employer and workplace, start and end date, duties, working
days and hours, break time, weekly rest day (주휴일), hourly wage, pay day and payment method,
bonuses and allowances, overtime premium, social insurance, whether a copy of the contract is
given to the worker.
Check for red flags such as: hourly wage below the legal minimum ({MIN_WAGE_2026_KRW:,} KRW per hour in
2026; mention it as a general reference and recommend checking); no weekly holiday pay for
workers over 15 hours a week; missing overtime premium (50% extra); cash payment with no record;
deductions or deposits taken from pay; unclear duties; penalties for quitting; work hours above
what the student visa permits.
For student work confirmations: weekly hour limits are 20 hours (language students and
undergraduates; 25 at certified universities) and 30 hours (master's/doctoral) when the Korean
language requirement is met; 10 hours (15 for graduate students) when it is not. Working before
the permit is issued can be punished for both the student and the employer. State this clearly.
Todos to consider: get the permit before starting, keep a signed copy of the contract, record
working hours, check that insurance is applied.
""",
}


def build_prompt(doc_type: DocType, lang: str, ocr_text: str) -> tuple[str, str]:
    """Return (system_prompt, user_prompt)."""
    if doc_type not in CHECKLISTS:
        raise ValueError(f"No prompt for document type {doc_type!r}")
    language = LANGUAGE_NAMES[lang]
    system = "\n".join([BASE_RULES.replace("{language}", language), CHECKLISTS[doc_type], JSON_SHAPE])
    user = f"DOCUMENT TEXT (OCR, pages in order):\n<<<\n{ocr_text}\n>>>"
    return system, user


def build_retry_prompt(error: str) -> str:
    return (
        "Your previous answer could not be used: "
        f"{error}\nReturn ONLY the corrected JSON object in the required shape."
    )
