"""Text-accuracy metrics for the evaluation scripts."""

from __future__ import annotations

from collections import Counter


def normalize(text: str) -> str:
    """Drop all whitespace: line breaks and spacing are layout, not recognition errors."""
    return "".join(text.split())


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance, two rows of memory."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(truth: str, hypothesis: str) -> float:
    """Character error rate = edits / length of the truth. Can be above 1."""
    t, h = normalize(truth), normalize(hypothesis)
    if not t:
        return 0.0 if not h else 1.0
    return edit_distance(t, h) / len(t)


def char_recall(truth: str, hypothesis: str) -> float:
    """Share of the true characters that appear in the output, ignoring their order.

    CER punishes a wrong reading order (two columns read in the wrong sequence) as heavily as
    wrong letters. Recall shows how much text was *read*, whatever order it came out in.
    """
    t, h = Counter(normalize(truth)), Counter(normalize(hypothesis))
    total = sum(t.values())
    return sum(min(n, h[c]) for c, n in t.items()) / total if total else 1.0
