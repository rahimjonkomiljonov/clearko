import pytest

from app.ocr import OCRLine, OCRResult, get_engine, sort_reading_order


def line(text, x0, y0, x1, y1, conf=0.9):
    return OCRLine(text, conf, (x0, y0, x1, y1))


def test_same_row_sorted_left_to_right_and_rows_top_to_bottom():
    lines = [
        line("C", 300, 100, 380, 130),
        line("A", 10, 98, 90, 128),
        line("B", 150, 102, 230, 132),
        line("D", 10, 200, 90, 230),
    ]
    assert [x.text for x in sort_reading_order(lines)] == ["A", "B", "C", "D"]


def test_slightly_different_heights_still_one_row():
    lines = [line("right", 400, 104, 500, 134), line("left", 10, 100, 100, 130)]
    assert [x.text for x in sort_reading_order(lines)] == ["left", "right"]


def test_result_helpers():
    r = OCRResult([line("a", 0, 0, 1, 1, 0.8), line("b", 0, 5, 1, 6, 0.6)])
    assert r.full_text == "a\nb"
    assert abs(r.mean_confidence - 0.7) < 1e-9
    assert OCRResult().mean_confidence == 0.0


def test_unknown_engine_rejected():
    with pytest.raises(ValueError):
        get_engine("nope")


# --- orientation fallback ---
import numpy as np

from app.ocr import OCREngine
from app.ocr.orient import recognize_upright


class FakeEngine(OCREngine):
    """Reads well only when the image's top-left pixel marker says it is upright."""

    name = "fake"

    def __init__(self):
        self.calls = 0

    def recognize(self, image):
        self.calls += 1
        upright = image[0, 0, 0] == 255
        if upright:
            return OCRResult([line("정상 텍스트입니다", 0, 0, 1, 1, 0.95)] * 5)
        return OCRResult([line("zz", 0, 0, 1, 1, 0.3)])


def make_marked(rotations_cw: int) -> np.ndarray:
    import cv2

    img = np.zeros((20, 30, 3), np.uint8)
    img[0, 0, 0] = 255  # marker in the upright top-left corner
    codes = [None, cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]
    return img if rotations_cw == 0 else cv2.rotate(img, codes[rotations_cw])


def test_upright_image_needs_one_call():
    eng = FakeEngine()
    result, deg = recognize_upright(eng, make_marked(0))
    assert deg == 0 and eng.calls == 1 and result.mean_confidence > 0.9


def test_rotated_image_is_recovered():
    for k in (1, 2, 3):  # input was rotated k*90 cw; undoing it needs (4-k)*90 cw
        result, deg = recognize_upright(FakeEngine(), make_marked(k))
        assert deg == (4 - k) * 90
        assert result.mean_confidence > 0.9


def test_empty_result_triggers_fallback_without_crashing():
    class Blank(OCREngine):
        name = "blank"

        def recognize(self, image):
            return OCRResult()

    result, deg = recognize_upright(Blank(), np.zeros((10, 10, 3), np.uint8))
    assert deg == 0 and result.lines == []


# --- script routing ---
from app.ocr.routing import ScriptRoutingEngine, hangul_ratio


class Fixed(OCREngine):
    name = "fixed"

    def __init__(self, texts):
        self.texts, self.calls = texts, 0

    def recognize(self, image):
        self.calls += 1
        return OCRResult([line(t, 0, i * 10, 1, i * 10 + 5) for i, t in enumerate(self.texts)])


def test_hangul_ratio():
    assert hangul_ratio("보증금 5,000,000원") == 1.0
    assert hangul_ratio("price 61,000 won") == 0.0
    assert hangul_ratio("12,345") == 0.0
    assert abs(hangul_ratio("계약 contract") - 0.2) < 1e-9


def test_korean_page_stays_on_korean_engine():
    ko, en = Fixed(["임대인과 임차인은 다음과 같이 계약을 체결한다 " * 3]), Fixed(["x"])
    router = ScriptRoutingEngine(ko, lambda: en)
    router.recognize(np.zeros((5, 5, 3), np.uint8))
    assert en.calls == 0 and router.last_language == "ko"


def test_english_page_is_rerouted_to_english_engine():
    ko = Fixed(["Thls plon requlres a 12-month contrcct and a 61,000 won fee ok"])
    en = Fixed(["This plan requires a 12-month contract and a 61,000 won fee"])
    router = ScriptRoutingEngine(ko, lambda: en)
    out = router.recognize(np.zeros((5, 5, 3), np.uint8))
    assert "61,000" in out.full_text and router.last_language == "en"


def test_short_text_is_not_rerouted():
    ko, en = Fixed(["OK"]), Fixed(["x"])
    ScriptRoutingEngine(ko, lambda: en).recognize(np.zeros((5, 5, 3), np.uint8))
    assert en.calls == 0
