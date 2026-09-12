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
    lines = ["RECORD OF RIGHTS - EXTRACT", "Village : Nigohan    Tehsil : Mohanlalganj", "District : Lucknow    State : Uttar Pradesh",
             "Name of Landowner : Ram Prasad Sharma", "Khata No. : 00245", "Khasra No. : 123/2", "Area : 0.412 Hectare"]
    for i, text in enumerate(lines):
        page.insert_text((50, 80 + 30 * i), text, fontsize=12)
    loaded_before = dict(engine_mod._engines)
    ocr = run_ocr(doc.tobytes(), "digital.pdf")
    assert ocr["engine"] == "pdf-text" and ocr["pages"][0]["preprocess"]["steps"] == ["pdf_text_layer"]
    assert engine_mod._engines == loaded_before  # the OCR model was never needed
    f = {k: v["value"] for k, v in extract(ocr)["fields"].items()}
    assert f["owner_name"] == "Ram Prasad Sharma" and f["khata_number"] == "00245" and f["khasra_number"] == "123/2"
    assert (f["village"], f["district"]) == ("Nigohan", "Lucknow")


def _ruled_table():
    """1200x900 page with a 2-row x 4-column ruled table and a digit-like blob per cell."""
    img = np.full((900, 1200), 255, np.uint8)
    xs, ys = [80, 330, 580, 880, 1120], [300, 370, 440]
    for x in xs:
        cv2.line(img, (x, ys[0]), (x, ys[-1]), 0, 2)
    for y in ys:
        cv2.line(img, (xs[0], y), (xs[-1], y), 0, 2)
    for i in range(2):
        for j in range(4):
            cv2.putText(img, "123", (xs[j] + 60, ys[i] + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    return img, xs, ys


def test_table_grid_detection():
    from backend.ocr.tables import cells_of, detect_tables
    img, xs, ys = _ruled_table()
    tables = detect_tables(img)
    assert len(tables) == 1
    t = tables[0]
    assert len(t["rows"]) == 3 and len(t["cols"]) == 5
    assert all(abs(a - b) <= 4 for a, b in zip(t["cols"], xs)) and all(abs(a - b) <= 4 for a, b in zip(t["rows"], ys))
    assert len(cells_of(t)) == 8
    assert detect_tables(_text_page()) == []  # plain text page: no table


class CellEngine:
    def __init__(self, conf):
        self.conf = conf

    def read_boxes(self, gray, boxes):
        return [{"text": "cell", "confidence": self.conf, "bbox": list(b)} for b in boxes]


def test_cell_reading_keeps_the_more_confident_reading():
    from backend.ocr.tables import read_table_cells
    img, xs, ys = _ruled_table()
    free = [{"text": "free", "confidence": 0.6, "bbox": [xs[j] + 55, ys[i] + 25, xs[j] + 120, ys[i] + 55]}
            for i in range(2) for j in range(4)]
    outside = {"text": "title", "confidence": 0.9, "bbox": [100, 100, 300, 130]}
    better, used = read_table_cells(img, free + [outside], CellEngine(0.9))
    assert used == 8 and sum(t["text"] == "cell" for t in better) == 8 and outside in better
    worse, used = read_table_cells(img, free + [outside], CellEngine(0.3))
    assert used == 0 and sorted(t["text"] for t in worse) == sorted(t["text"] for t in free + [outside])


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


def test_badly_read_page_gets_a_second_read(monkeypatch):
    """A page that reads badly is read again with lighter denoising, and that reading is kept."""
    from backend.ocr import pipeline

    reads = []

    class Eng:
        name = "fake"
        languages = ["hi", "en"]

        def recognize(self, gray):
            reads.append(gray.shape)
            conf = 0.05 if len(reads) == 1 else 0.9  # first read poor, second read fine
            return [{"text": "क", "confidence": conf, "bbox": [40 * i, 40, 40 * i + 30, 70]} for i in range(8)]

        def sample_confidence(self, gray, boxes):
            return 0.9

    monkeypatch.setattr(pipeline, "get_engine", lambda name: Eng())
    png = cv2.imencode(".png", _text_page())[1].tobytes()
    out = pipeline.run_ocr(png, "page.png")

    steps = out["pages"][0]["preprocess"]["steps"]
    assert len(reads) == 2, "a poor page should be read a second time"
    assert "second read" in steps and any(s.startswith("denoise h") for s in steps)
    assert out["pages"][0]["quality"]["verdict"] == "good"  # the second reading is the one kept


def test_well_read_page_is_read_once(monkeypatch):
    from backend.ocr import pipeline

    reads = []

    class Eng:
        name = "fake"
        languages = ["hi", "en"]

        def recognize(self, gray):
            reads.append(gray.shape)
            return [{"text": "क", "confidence": 0.8, "bbox": [40 * i, 40, 40 * i + 30, 70]} for i in range(8)]

        def sample_confidence(self, gray, boxes):
            return 0.9

    monkeypatch.setattr(pipeline, "get_engine", lambda name: Eng())
    png = cv2.imencode(".png", _text_page())[1].tobytes()
    out = pipeline.run_ocr(png, "page.png")
    assert len(reads) == 1 and "second read" not in out["pages"][0]["preprocess"]["steps"]


class FakeNumberEngine:
    """Main model unsure about the numbers; the english-only reader gets them right."""
    name = "fake"

    def __init__(self, answers):
        self.answers = answers
        self.asked: list[list[int]] = []

    def read_numbers(self, image, boxes):
        self.asked = list(boxes)
        return [self.answers.get(tuple(b)) for b in boxes]


def test_unsure_numbers_are_read_again_in_english():
    from backend.ocr.numbers import refine_numbers

    tokens = [
        {"text": "/q0/4", "confidence": 0.21, "bbox": [0, 0, 10, 10]},
        {"text": "Tehsil", "confidence": 0.30, "bbox": [0, 20, 10, 30]},      # not a number
        {"text": "1124/6\u0915", "confidence": 0.18, "bbox": [0, 40, 10, 50]},  # has a devanagari letter
        {"text": "00806", "confidence": 0.97, "bbox": [0, 60, 10, 70]},       # already confident
    ]
    eng = FakeNumberEngine({(0, 0, 10, 10): {"text": "190/4", "confidence": 0.81}})
    assert refine_numbers(None, tokens, eng) == 1
    assert eng.asked == [[0, 0, 10, 10]]  # only the unsure number was asked about
    assert tokens[0]["text"] == "190/4" and tokens[0]["confidence"] == 0.81
    assert [t["text"] for t in tokens[1:]] == ["Tehsil", "1124/6\u0915", "00806"]


def test_a_worse_or_non_numeric_second_reading_is_ignored():
    from backend.ocr.numbers import refine_numbers

    tokens = [
        {"text": "/q0/4", "confidence": 0.45, "bbox": [0, 0, 10, 10]},
        {"text": "S45", "confidence": 0.25, "bbox": [0, 20, 10, 30]},
    ]
    eng = FakeNumberEngine({
        (0, 0, 10, 10): {"text": "190/4", "confidence": 0.52},   # only 0.07 better
        (0, 20, 10, 30): {"text": "//-.", "confidence": 0.90},   # confident, but not a number
    })
    assert refine_numbers(None, tokens, eng) == 0
    assert [t["text"] for t in tokens] == ["/q0/4", "S45"]


def test_an_engine_without_a_number_reader_is_left_alone():
    from backend.ocr.numbers import refine_numbers

    tokens = [{"text": "/q0/4", "confidence": 0.21, "bbox": [0, 0, 10, 10]}]
    assert refine_numbers(None, tokens, object()) == 0


def test_a_number_written_in_devanagari_digits_is_left_alone():
    """The english reader has no Devanagari: asked to re-read "\u0966\u0968/\u0966\u0969/\u0968\u0966\u0966\u0968" it answers
    "03/03/3002". Extraction reads Devanagari digits, so that token was already right."""
    from backend.ocr.numbers import looks_numeric

    assert not looks_numeric("\u0966\u0968/\u0966\u0969/\u0968\u0966\u0966\u0968")   # a date, read correctly
    assert not looks_numeric("\u0968\u096b\u0967\u096c")                             # a plain number
    assert not looks_numeric("\u0966\u0968|\u0966\u096f/\u0968\u0966\u0967\u096f")   # with a stray bar in it
    assert looks_numeric("/\u0967\u09676/\u096b\u0966\u096b\u096b\u0966")            # mixed scripts: a bad read
    assert looks_numeric("S\u096a\u096b")                                            # a letter no number can hold
    assert looks_numeric("0109") and looks_numeric("190/4") and looks_numeric("3.598")


def test_words_and_khasra_letters_are_not_numbers():
    from backend.ocr.numbers import looks_numeric

    assert not looks_numeric("Tehsil")
    assert not looks_numeric("\u0916\u0938\u0930\u093e")       # खसरा
    assert not looks_numeric("1124/6\u0915")                   # 1124/6क - the letter would be lost
    assert not looks_numeric("")
