from app.metrics import cer, char_recall, edit_distance, normalize


def test_edit_distance_basics():
    assert edit_distance("", "") == 0
    assert edit_distance("abc", "abc") == 0
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance("임대인", "임대") == 1
    assert edit_distance("abc", "") == 3


def test_whitespace_is_ignored():
    assert normalize(" 임 대\n인 ") == "임대인"
    assert cer("임대인 계약", "임대인계약\n") == 0.0


def test_cer_counts_wrong_and_missing_characters():
    assert cer("보증금 1,000", "보증금 1,000") == 0.0
    assert abs(cer("보증금1000", "보증금l000") - 1 / 7) < 1e-9  # 1 wrong digit of 7
    assert cer("abcd", "ab") == 0.5
    assert cer("ab", "abcd") == 1.0  # extra text counts too, so it can reach 1 and beyond
    assert cer("", "") == 0.0


def test_recall_ignores_order():
    assert char_recall("가나다라", "라다나가") == 1.0
    assert cer("가나다라", "라다나가") > 0.5  # but CER does not
    assert char_recall("가나다라", "가나") == 0.5
    assert char_recall("", "x") == 1.0
