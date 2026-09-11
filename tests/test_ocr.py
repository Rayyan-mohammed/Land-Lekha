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


def test_text_layer_accepts_real_text_and_rejects_legacy_font_gibberish():
    from backend.ocr.pipeline import text_layer_usable
    hindi = "खातेदार का नाम : राम प्रसाद खाता संख्या 00245 खसरा संख्या 123/2 ग्राम रामपुर तहसील सदर जिला लखनऊ".split()
    assert text_layer_usable(hindi)
    english = "Name of Landowner Ram Prasad Khata No 00245 Khasra No 123/2 Village Rampur Tehsil Sadar District".split()
    assert text_layer_usable(english)
    kruti_dev = "[kkrsnkj dk uke jke izlkn [kkrk la[;k 00245 [kljk la[;k xzke jkeiqj rglhy lnj ftyk y[kuÅ".split()
    assert not text_layer_usable(kruti_dev)   # pre-Unicode Hindi font: must go to OCR
    assert not text_layer_usable(["Village", "Rampur"])  # too little text (e.g. a scan's stray layer)


def test_digital_pdf_is_read_without_ocr():
    import fitz
    from backend.extraction.extractor import extract
    from backend.ocr import engine as engine_mod
    from backend.ocr.pipeline import run_ocr

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    lines = ["RECORD OF RIGHTS - EXTRACT", "Village : Nigoha    Tehsil : Mohanlalganj", "District : Lucknow    State : Uttar Pradesh",
             "Name of Landowner : Ram Prasad Sharma", "Khata No. : 00245", "Khasra No. : 123/2", "Area : 0.412 Hectare"]
    for i, text in enumerate(lines):
        page.insert_text((50, 80 + 30 * i), text, fontsize=12)
    loaded_before = dict(engine_mod._engines)
    ocr = run_ocr(doc.tobytes(), "digital.pdf")
    assert ocr["engine"] == "pdf-text" and ocr["pages"][0]["preprocess"]["steps"] == ["pdf_text_layer"]
    assert engine_mod._engines == loaded_before  # the OCR model was never needed
    f = {k: v["value"] for k, v in extract(ocr)["fields"].items()}
    assert f["owner_name"] == "Ram Prasad Sharma" and f["khata_number"] == "00245" and f["khasra_number"] == "123/2"
    assert (f["village"], f["district"]) == ("Nigoha", "Lucknow")


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
