"""Make SYNTHETIC filled-in part-time job documents (fake names, deliberate problems) and
phone-style photos of them, for testing ClearKo. Nothing here is a real person or company.

    cd backend && .venv/Scripts/python.exe ../eval/tools/make_synthetic_parttime.py

Output (eval/data/synthetic/):  <name>.pdf (clean), <name>_photo.jpg (phone-style), and
<name>_expected.md (the problems a good explanation must find).
Needs PyMuPDF and the Windows font Malgun Gothic.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pymupdf as fitz

OUT = Path(__file__).resolve().parents[1] / "data" / "synthetic"
FONT_FILE = r"C:\Windows\Fonts\malgun.ttf"
FONT_BOLD_FILE = r"C:\Windows\Fonts\malgunbd.ttf"
PAGE_W, PAGE_H = 595, 842  # A4 in points
MARGIN = 50

Line = tuple[str, float, bool]  # text, font size, bold


class Writer:
    """Minimal top-to-bottom text writer with word wrapping and page breaks."""

    def __init__(self, doc: fitz.Document):
        self.doc = doc
        self.regular = fitz.Font(fontfile=FONT_FILE)
        self.bold = fitz.Font(fontfile=FONT_BOLD_FILE)
        self.page = self._new_page()

    def _new_page(self) -> fitz.Page:
        page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        page.insert_font(fontname="mg", fontfile=FONT_FILE)
        page.insert_font(fontname="mgb", fontfile=FONT_BOLD_FILE)
        self.y = MARGIN
        return page

    def _wrap(self, text: str, size: float, bold: bool, width: float) -> list[str]:
        font = self.bold if bold else self.regular
        lines, cur = [], ""
        for ch in text:
            if font.text_length(cur + ch, fontsize=size) > width:
                lines.append(cur)
                cur = ch.lstrip()
            else:
                cur += ch
        lines.append(cur)
        return lines

    def write(self, text: str, size: float = 10, bold: bool = False, indent: float = 0,
              gap: float = 4, center: bool = False) -> None:
        width = PAGE_W - 2 * MARGIN - indent
        for part in self._wrap(text, size, bold, width):
            if self.y + size * 1.5 > PAGE_H - MARGIN:
                self.page = self._new_page()
            x = MARGIN + indent
            if center:
                font = self.bold if bold else self.regular
                x = (PAGE_W - font.text_length(part, fontsize=size)) / 2
            self.page.insert_text((x, self.y + size), part, fontsize=size,
                                  fontname="mgb" if bold else "mg")
            self.y += size * 1.45
        self.y += gap

    def rule(self) -> None:
        self.page.draw_line((MARGIN, self.y), (PAGE_W - MARGIN, self.y), width=0.6)
        self.y += 6


def save(doc: fitz.Document, path: Path) -> None:
    doc.subset_fonts()  # keep only the glyphs used: the full Malgun font is ~13 MB
    doc.save(path, garbage=4, deflate=True)


def labor_contract(path: Path) -> None:
    doc = fitz.open()
    w = Writer(doc)
    w.write("표준근로계약서 (단시간근로자)", 17, True, center=True, gap=12)
    w.write('행복분식 김민수(이하 "사업주"라 함)과(와) AZIZ KARIMOV(이하 "근로자"라 함)은 '
            "다음과 같이 근로계약을 체결한다.", 10.5, gap=10)
    items = [
        "1. 근로개시일 : 2026년 9월 1일부터 2027년 2월 28일까지",
        "2. 근무장소 : 경기도 성남시 수정구 태평로 100 행복분식",
        "3. 업무의 내용 : 주방 보조 및 기타 사업주가 지시하는 모든 업무",
        "4. 소정근로시간 : 18시 00분부터 23시 00분까지 (휴게시간 : 없음)",
        "5. 근무일/휴일 : 매주 월, 화, 수, 목, 금요일 근무 / 주휴일 : 없음",
        "6. 임금",
        "   - 시간급 : 9,000원",
        "   - 상여금 : 없음   - 기타급여(제수당 등) : 없음",
        "   - 연장·야간근로수당 : 지급하지 않음 (포괄하여 시급에 포함됨)",
        "   - 임금지급일 : 매월 말일 / 지급방법 : 현금으로 직접 지급",
        "7. 연차유급휴가 : 해당 없음",
        "8. 사회보험 적용여부 : 고용보험 [ ]  산재보험 [ ]  국민연금 [ ]  건강보험 [ ]  (가입하지 않음)",
        "9. 근로계약서 교부 : 본 계약서는 사업주가 보관하며 근로자에게 교부하지 않는다.",
    ]
    for it in items:
        w.write(it, 10.5, gap=3)
    w.rule()
    w.write("[특약사항]", 11, True, gap=4)
    specials = [
        ("1) 근로자가 계약기간 중 퇴사하려면 1개월 전에 통보해야 하며, 통보하지 않을 경우 마지막 달 "
         "임금의 50%를 공제한다."),
        "2) 유니폼 및 파손된 물품의 비용은 근로자가 부담하며 임금에서 공제한다.",
        "3) 근로자는 입사 시 보증금 30만원을 사업주에게 맡기며, 퇴사 시 사업주가 판단하여 반환한다.",
        "4) 근로자는 업무와 관련한 사항을 외부에 알리지 않으며, 위반 시 손해를 배상한다.",
        "5) 이 계약에 정함이 없는 사항은 사업주의 지시에 따른다.",
    ]
    for s in specials:
        w.write(s, 10.5, indent=6, gap=3)
    w.rule()
    w.write("2026년 8월 25일", 10.5, gap=8, center=True)
    w.write("(사업주) 사업체명 : 행복분식    대표자 : 김민수 (인)", 10.5, gap=3)
    w.write("(근로자) 성명 : AZIZ KARIMOV (서명)", 10.5)
    save(doc, path)


def student_confirmation(path: Path) -> None:
    doc = fitz.open()
    w = Writer(doc)
    w.write("시간제취업 확인서", 18, True, center=True, gap=4)
    w.write("(외국인 유학생 시간제취업 확인서 / Confirmation of Part-time Employment)", 9.5,
            center=True, gap=12)
    w.write("1. 유학생 인적사항", 11, True)
    rows1 = [
        "성명 : AZIZ KARIMOV      국적 : 우즈베키스탄      외국인등록번호 : 000000-0000000",
        "학교 : 한국샘플대학교      학과 : 경영학과      학위과정 : 학사 (2학년)",
        "체류자격 : D-2      한국어능력 : TOPIK 2급",
    ]
    for r in rows1:
        w.write(r, 10.5, gap=3)
    w.rule()
    w.write("2. 시간제취업 내용", 11, True)
    rows2 = [
        "근무처 : 행복분식 (사업자등록번호 000-00-00000)      대표자 : 김민수",
        "근무처 주소 : 경기도 성남시 수정구 태평로 100",
        "업종 : 음식점업      업무내용 : 주방 보조 및 서빙",
        "근무기간 : 2026년 9월 1일 ~ 2027년 2월 28일",
        "근무요일 및 시간 : 월~금 18:00 ~ 23:00, 토 10:00 ~ 18:00 (주 33시간)",
        "시급 : 9,000원      임금지급방법 : 현금",
    ]
    for r in rows2:
        w.write(r, 10.5, gap=3)
    w.rule()
    w.write("3. 확인", 11, True)
    w.write("위 외국인 유학생은 위와 같이 시간제취업을 하고자 하며, 사업주는 출입국관리법령에 따른 "
            "시간제취업 허가 조건을 준수할 것을 확인합니다. 근무는 2026년 9월 1일부터 시작하였습니다.",
            10.5, gap=8)
    w.write("작성일 : 2026년 9월 15일", 10.5, gap=10)
    w.write("사업주 : 김민수 (인)", 10.5, gap=3)
    w.write("유학생 : AZIZ KARIMOV (서명)", 10.5, gap=3)
    w.write("학교 유학생 담당자 확인 : (미기재)", 10.5, gap=3)
    w.write("출입국·외국인관서 허가번호 : (미기재)", 10.5)
    save(doc, path)


def render(pdf: Path) -> list[np.ndarray]:
    pages = []
    for page in fitz.open(pdf):
        pix = page.get_pixmap(dpi=170)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        pages.append(cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2BGR))
    return pages


def phone_photo(page: np.ndarray, seed: int) -> np.ndarray:
    """Paper on a dark desk, tilted, uneven light, slight blur and noise, JPEG artefacts."""
    rng = np.random.default_rng(seed)
    h, w = page.shape[:2]
    canvas_w, canvas_h = int(w * 1.25), int(h * 1.12)
    desk = np.full((canvas_h, canvas_w, 3), (60, 70, 85), np.uint8)
    ox, oy = (canvas_w - w) // 2, (canvas_h - h) // 2
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    jitter = rng.uniform(-0.025, 0.025, (4, 2)) * np.array([w, h])
    dst = (src + np.float32([ox, oy]) + jitter.astype(np.float32)).astype(np.float32)
    warp = cv2.getPerspectiveTransform(src, dst)
    paper = cv2.warpPerspective(page, warp, (canvas_w, canvas_h), borderValue=(0, 0, 0))
    mask = cv2.warpPerspective(np.full((h, w), 255, np.uint8), warp, (canvas_w, canvas_h))
    rot = cv2.getRotationMatrix2D((canvas_w / 2, canvas_h / 2), float(rng.uniform(-3, 3)), 1.0)
    paper = cv2.warpAffine(paper, rot, (canvas_w, canvas_h), borderValue=(0, 0, 0))
    mask = cv2.warpAffine(mask, rot, (canvas_w, canvas_h))
    img = np.where(mask[..., None] > 0, paper, desk)
    # uneven lighting: brighter on one side
    xs = np.linspace(0.82, 1.08, canvas_w, dtype=np.float32)[None, :, None]
    img = (img.astype(np.float32) * xs).clip(0, 255)
    img = cv2.GaussianBlur(img, (0, 0), 0.9)
    img = img + rng.normal(0, 3.5, img.shape)
    img = img.clip(0, 255).astype(np.uint8)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("parttime_contract", labor_contract, 1),
        ("student_confirmation", student_confirmation, 2),
    ]
    for name, make, seed in jobs:
        pdf = OUT / f"{name}.pdf"
        make(pdf)
        for i, page in enumerate(render(pdf), 1):
            photo = phone_photo(page, seed * 10 + i)
            suffix = "" if i == 1 else f"_p{i}"
            cv2.imwrite(str(OUT / f"{name}_photo{suffix}.jpg"), photo, [cv2.IMWRITE_JPEG_QUALITY, 72])
        print("wrote", pdf.name)
    (OUT / "parttime_contract_expected.md").write_text(EXPECTED_CONTRACT, encoding="utf-8")
    (OUT / "student_confirmation_expected.md").write_text(EXPECTED_STUDENT, encoding="utf-8")


EXPECTED_CONTRACT = """# parttime_contract: problems a good explanation must find (synthetic)

Hourly wage 9,000 KRW is below the 2026 minimum wage (10,320 KRW; verify).
No weekly holiday (주휴일: 없음) although 25 hours a week, no holiday pay.
No overtime/night premium (night work after 22:00 is in the hours).
No break time for a 5-hour shift is acceptable, but note it.
Cash payment with no payslip/record.
No social insurance (all four boxes empty).
Contract is kept by the employer, no copy for the worker (Labor Standards Act art. 17).
Special terms: 50% of last month's wage withheld if no 1 month notice; uniform/breakage cost deducted
from wages; 300,000 KRW deposit kept by the employer; confidentiality with damages;
"anything not agreed follows the employer's instructions".
"""

EXPECTED_STUDENT = """# student_confirmation: problems a good explanation must find (synthetic)

33 hours a week is far above the limit for an undergraduate with TOPIK 2 (10 hours when the
language requirement is not met; 20-25 when it is).
Work started on 1 Sep 2026 but the form is dated 15 Sep and the permit number is empty:
working before the permit is issued can be punished (student and employer).
School international-office confirmation is empty.
Wage 9,000 KRW is below the 2026 minimum wage (10,320 KRW; verify); paid in cash.
"""

if __name__ == "__main__":
    main()
