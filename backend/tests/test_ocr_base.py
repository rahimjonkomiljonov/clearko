from app.ocr import OCRLine, OCRResult, get_engine, sort_reading_order
import pytest


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
