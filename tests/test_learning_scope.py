"""What a remembered correction is allowed to decide on its own."""
from backend.extraction.extractor import extract
from backend.extraction.learning import CorrectionMemory


def _ocr(lines):
    tokens, out = [], []
    for i, text in enumerate(lines):
        y = 100 + i * 50
        box = [80, y, 80 + 20 * len(text), y + 30]
        tokens.append({"text": text, "confidence": 0.95, "bbox": box})
        out.append({"text": text, "confidence": 0.95, "bbox": box, "token_ids": [i]})
    return {"engine": "test", "languages": ["hi", "en"], "elapsed_ms": 0,
            "pages": [{"page": 1, "width": 1240, "height": 900, "tokens": tokens, "lines": out}]}


PAGE = ["खतौनी", "ग्राम : निगोह   तहसील : मोहनलालगंज", "जिला : लखनऊ   राज्य : उत्तर प्रदेश",
        "खातेदार का नाम : राम प्रसाद शर्मा", "खाता संख्या : 00245", "खसरा संख्या : 123/2",
        "क्षेत्रफल : 0.412 हेक्टेयर"]


def test_a_learned_name_stands_on_its_own():
    """A name misread the same way means the same person next time."""
    mem = CorrectionMemory()
    mem.add_correction("owner_name", "राम प्रसाद शर्मा", "राम प्रसाद वर्मा")
    f = extract(_ocr(PAGE), memory=mem)["fields"]["owner_name"]
    assert f["value"] == "राम प्रसाद वर्मा"
    assert f["confidence"] > 0.8
    assert not any("confirm" in i for i in f["issues"])


def test_a_learned_place_is_still_checked_against_the_gazetteer():
    """Memory raises the confidence; the master data still decides the official spelling."""
    mem = CorrectionMemory()
    mem.add_correction("village", "निगोह", "Nigoha")
    with_memory = extract(_ocr(PAGE), memory=mem)["fields"]["village"]
    without = extract(_ocr(PAGE))["fields"]["village"]
    assert with_memory["value"] == without["value"] == "Nigohan"
    assert with_memory["confidence"] > without["confidence"]


def test_a_learned_khasra_number_is_only_a_suggestion():
    """A khasra number identifies the parcel and differs from record to record. A memory keyed
    on a misreading must not quietly write last week's number onto this week's plot."""
    mem = CorrectionMemory()
    mem.add_correction("khasra_number", "123/2", "456/7")
    f = extract(_ocr(PAGE), memory=mem)["fields"]["khasra_number"]
    assert f["value"] == "456/7"                      # shown, so the verifier sees it
    assert f["confidence"] < 0.8                      # but not trusted
    assert any("confirm" in i for i in f["issues"])


def test_a_suggested_number_keeps_the_document_in_review():
    mem = CorrectionMemory()
    mem.add_correction("khata_number", "00245", "00999")
    ext = extract(_ocr(PAGE), memory=mem, threshold=0.5)
    assert ext["route"] == "review"
    assert any("khata_number" in r for r in ext["route_reasons"])


def test_areas_and_dates_are_suggestions_too():
    from backend.extraction.extractor import LEARNING_DECIDES

    for name in ("plot_area", "mutation_date", "registration_date", "survey_number",
                 "khata_number", "khasra_number", "mutation_number", "registration_number"):
        assert name not in LEARNING_DECIDES, f"{name} must not be decided by memory alone"
