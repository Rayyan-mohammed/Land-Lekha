"""Fast tests for OCR-side logic (no OCR model needed).

    python -m pytest tests -q
"""
import cv2
import numpy as np

from backend.ocr.pipeline import fix_upside_down
from backend.ocr.preprocess import is_sideways
from backend.ocr.quality import assess


def _text_page(h=1400, w=1000):
    """White page with horizontal black 'text lines' made of word-like blocks."""
    img = np.full((h, w), 255, np.uint8)
    rng = np.random.default_rng(0)
    for y in range(100, h - 100, 45):
        x = 80
        while x < w - 150:
            ww = int(rng.integers(30, 110))
            cv2.rectangle(img, (x, y), (x + ww, y + 18), 0, -1)
            x += ww + int(rng.integers(12, 30))
    return img


def test_sideways_detection():
    page = _text_page()
    assert not is_sideways(page)
    assert is_sideways(cv2.rotate(page, cv2.ROTATE_90_CLOCKWISE))
    assert is_sideways(cv2.rotate(page, cv2.ROTATE_90_COUNTERCLOCKWISE))


class FakeEngine:
    """Reads well only when the page's marker pixel is in the top-left (i.e. upright)."""
    def __init__(self):
        self.recognized = 0

    def _upright(self, gray):
        return gray[0, 0] == 0

    def recognize(self, gray):
        self.recognized += 1
        c = 0.9 if self._upright(gray) else 0.05
        return [{"text": "x", "confidence": c, "bbox": [10 * i, 10, 10 * i + 8, 20]} for i in range(6)]

    def sample_confidence(self, gray, boxes):
        return 0.9 if self._upright(gray) else 0.05


def test_upside_down_page_is_flipped():
    page = np.full((100, 80), 255, np.uint8)
    page[0, 0] = 0
    flipped = cv2.rotate(page, cv2.ROTATE_180)
    eng = FakeEngine()
    tokens = eng.recognize(flipped)
    out, new_tokens, did = fix_upside_down(flipped, tokens, eng)
    assert did and out[0, 0] == 0 and new_tokens[0]["confidence"] == 0.9


def test_upright_confident_page_costs_nothing():
    page = np.full((100, 80), 255, np.uint8)
    page[0, 0] = 0
    eng = FakeEngine()
    tokens = eng.recognize(page)
    out, _, did = fix_upside_down(page, tokens, eng)
    assert not did and eng.recognized == 1  # no second recognition pass


def _tokens(conf, n=20, height=30):
    return [{"text": "t", "confidence": conf, "bbox": [0, 0, 50, height]} for _ in range(n)]


def test_quality_verdicts_and_advice():
    sharp = _text_page()
    assert assess(sharp, _tokens(0.8), (1754, 1240))["verdict"] == "good"
    assert assess(sharp, _tokens(0.3), (1754, 1240))["verdict"] == "fair"
    blurred = cv2.GaussianBlur(sharp, (0, 0), 4)
    poor = assess(blurred, _tokens(0.1, height=10), (700, 500))
    assert poor["verdict"] == "poor"
    text = " ".join(poor["advice"])
    assert "blurred" in text and "small" in text and "resolution" in text
    assert assess(sharp, [], (1754, 1240))["verdict"] == "poor"
