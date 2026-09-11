"""Fast tests for the extraction layer (no OCR model needed).

    python -m pytest tests -q
"""
from backend.extraction import gazetteer
from backend.extraction.confidence import route
from backend.extraction.duplicates import find_duplicates
from backend.extraction.extractor import extract
from backend.extraction.learning import CorrectionMemory
from backend.extraction.names import restore
from backend.extraction.normalize import skeleton
from backend.extraction.parser import split_owners
from backend.extraction.validate import parse_area, parse_date, parse_name, parse_plain_number, parse_plot_id, parse_registration


def test_numbers_fix_ocr_lookalikes_and_devanagari_digits():
    assert parse_plain_number("OO245").value == "00245"
    assert parse_plain_number("०२४५").value == "0245"
    assert parse_plain_number("abc").value is None


def test_plot_ids_keep_suffix_and_repair_slash():
    assert parse_plot_id("123/2क").value == "123/2क"
    assert parse_plot_id("45/1B").value == "45/1B"  # B is a suffix here, not an 8
    assert parse_plot_id("810|5").value == "810/5"


def test_plot_id_suffix_confusion_and_unreadable_sub_number():
    assert parse_plot_id("1819/9स").value == "1819/9ख"
    p = parse_plot_id("39/^")
    assert p.value == "39" and not p.valid  # flagged, not silently trusted


def test_area_without_decimal_point_is_recovered_or_flagged():
    p = parse_area("089", unit_hint="acre")
    assert p.normalized["value"] == 0.89 and "decimal point inferred" in p.issues
    q = parse_area("183 bigha")
    assert q.normalized["value"] == 183 and "no decimal point - check value" in q.issues and q.rule_score < 1
    assert parse_area("5 bigha").issues == []  # small whole numbers are normal
    assert parse_area("0.25", unit_hint=None, default_unit=None).normalized["unit"] == "hectare"


def test_unit_word_with_one_misread_letter():
    from backend.extraction.validate import find_unit
    assert find_unit("(एझड") == "acre"
    assert find_unit("(हेक्टेयर)") == "hectare"


def test_dates_are_validated():
    assert parse_date("16/01/2008").value == "16/01/2008"
    assert parse_date("25/12|2006").value == "25/12/2006"
    assert not parse_date("31/02/2010").valid
    assert not parse_date("no date").valid


def test_registration_number():
    assert parse_registration("2006/59905").value == "2006/59905"
    assert parse_registration("1999|90540").value == "1999/90540"


def test_area_units_and_decimal_recovery():
    p = parse_area("3.48 एकड़")
    assert p.normalized == {"value": 3.48, "unit": "acre", "hectares": round(3.48 * 0.404686, 4)}
    assert parse_area("11.2 Bigha", bigha_ha=0.2529).normalized["unit"] == "bigha"
    lost = parse_area("3 48 acre")  # decimal point dropped by OCR
    assert lost.normalized["value"] == 3.48 and "decimal point inferred" in lost.issues
    table = parse_area("2.325", unit_hint="hectare")  # unit only in the table header
    assert table.normalized["unit"] == "hectare" and table.valid


def test_names_drop_label_residue_and_restore_diacritics():
    assert parse_name("s Name Bharat Prasad Srivastava").value == "Bharat Prasad Srivastava"
    assert parse_name("राजेश प्रसाद सिह").value == "राजेश प्रसाद सिंह"
    words, changed = restore(["Kamnla", "Rathore"])
    assert words == ["Kamla", "Rathore"] and changed


def test_skeleton_ignores_dropped_marks():
    assert skeleton("खाता संख्या")[0] == skeleton("खाता सख्या")[0]
    assert skeleton("क्षेत्रफल")[0] == skeleton("कषेत्रफल")[0]


def test_gazetteer_matches_both_scripts_and_checks_hierarchy():
    place, score = gazetteer.best_match("district", "लखनऊ")
    assert place.en == "Lucknow" and score == 1.0
    out, checks = gazetteer.resolve({"district": "Lucknow", "tehsil": "मोहनलालगंज", "village": "अब्बास नागार"})
    assert out["village"][0].en == "Abbas Nagar"
    assert all(c["ok"] for c in checks)
    _, bad = gazetteer.resolve({"district": "Lucknow", "tehsil": "Pindra"})
    assert not next(c for c in bad if c["check"] == "tehsil_in_district")["ok"]


def _ocr(lines):
    """Build a one-page OCR result where each line is one token."""
    tokens, out_lines = [], []
    for i, (text, conf) in enumerate(lines):
        y = 100 + i * 50
        tokens.append({"text": text, "confidence": conf, "bbox": [80, y, 80 + 20 * len(text), y + 30]})
        out_lines.append({"text": text, "confidence": conf, "bbox": tokens[-1]["bbox"], "token_ids": [i]})
    return {"engine": "test", "languages": ["hi", "en"], "elapsed_ms": 0,
            "pages": [{"page": 1, "width": 1240, "height": 1754, "tokens": tokens, "lines": out_lines}]}


def test_end_to_end_key_value_record():
    ocr = _ocr([
        ("खतौनी (अधिकार अभिलेख)", 0.9),
        ("ग्राम : अब्बास नागार   तहसील : मोहनलालगंज", 0.95),
        ("जिला : लखनऊ   राज्य : उत्तर प्रदेश", 0.95),
        ("खातेदार का नाम : राम प्रसाद शर्मा", 0.9),
        ("खाता संख्या : 00245", 0.97),
        ("खसरा संख्या : 123/2", 0.97),
        ("क्षेत्रफल : 0.412 हेक्टेयर", 0.95),
        ("भूमि का प्रकार : कृषि (सिंचित)", 0.9),
        ("नामांतरण संख्या : 4521   नामांतरण दिनांक : 12/03/2019", 0.95),
    ])
    ext = extract(ocr)
    f = {k: v["value"] for k, v in ext["fields"].items()}
    assert ext["document_type"] == "khatauni"
    assert f["owner_name"] == "राम प्रसाद शर्मा"
    assert f["khata_number"] == "00245" and f["khasra_number"] == "123/2"
    assert ext["fields"]["plot_area"]["normalized"]["hectares"] == 0.412
    assert (f["village"], f["tehsil"], f["district"], f["state"]) == ("Abbas Nagar", "Mohanlalganj", "Lucknow", "Uttar Pradesh")
    assert f["land_classification"] == "agricultural_irrigated"
    assert f["mutation_number"] == "4521" and f["mutation_date"] == "12/03/2019"
    assert ext["missing_required"] == []


def test_tehsildar_signature_is_not_a_tehsil_label():
    ocr = _ocr([("Village : Tarenga Tehsil : Masaurhi", 0.95), ("District : Patna", 0.95), ("TEHSILDAR", 0.9)])
    assert extract(ocr)["fields"]["tehsil"]["value"] == "Masaurhi"


def test_route_sends_missing_and_inconsistent_to_review():
    decision, reasons = route({}, [{"check": "tehsil_in_district", "ok": False, "detail": "x"}], threshold=0.8)
    assert decision == "review"
    assert any("missing required field" in r for r in reasons)
    assert any("consistency failed" in r for r in reasons)


def test_duplicates_same_parcel():
    rec = {"district": "Lucknow", "village": "Nigoha", "khasra_number": "123/2", "khata_number": "00245", "owner_name": "राम प्रसाद शर्मा"}
    dups = find_duplicates(rec, [{**rec, "record_id": 7}, {**rec, "village": "Rampur", "record_id": 8}])
    assert [d["record_id"] for d in dups] == [7]


def test_duplicates_match_any_parcel_row_and_any_owner():
    # a multi-row khata: only the second parcel and second owner match an existing record
    rec = {"district": "Lucknow", "village": "Nigoha", "khata_number": "00245",
           "owners": [{"owner_name": "राम प्रसाद शर्मा"}, {"owner_name": "श्याम लाल शर्मा"}],
           "parcels": [{"khasra_number": "123/1"}, {"khasra_number": "456/2"}]}
    existing = {"record_id": 9, "district": "Lucknow", "village": "Nigoha", "khata_number": "99999",
                "owners": [{"owner_name": "श्याम लाल शर्मा"}], "parcels": [{"khasra_number": "456/2"}]}
    dups = find_duplicates(rec, [existing])
    assert [d["record_id"] for d in dups] == [9]


def test_split_owners_on_whole_words_only():
    assert split_owners("राम प्रसाद शर्मा एवं श्याम लाल शर्मा") == ["राम प्रसाद शर्मा", "श्याम लाल शर्मा"]
    assert split_owners("Ram Sharma, Shyam Sharma and Gita Devi") == ["Ram Sharma", "Shyam Sharma", "Gita Devi"]
    # "व" must not match mid-word inside a name like Shrivastava written in Devanagari
    assert split_owners("राजेश श्रीवास्तव") == ["राजेश श्रीवास्तव"]
    assert split_owners("1. Ram Lal  2. Shyam Lal") == ["Ram Lal", "Shyam Lal"]
    # OCR drops the anusvara: "एवं" arrives as "एव" (seen on the multi-owner eval split)
    assert split_owners("सुनीता त्रिपाठी एव सीता त्रिपाठी") == ["सुनीता त्रिपाठी", "सीता त्रिपाठी"]
    assert split_owners("राम एवम् श्याम") == ["राम", "श्याम"]
    assert split_owners("एच. आर. शर्मा") == ["एच. आर. शर्मा"]  # "एच" (H.) is a name initial, not "and"
    assert split_owners("एच आर शर्मा") == ["एच आर शर्मा"]      # ...even without the full stop, at the start
    assert split_owners("शिव प्रसाद अंसारी एच राम लाल अंसारी") == ["शिव प्रसाद अंसारी", "राम लाल अंसारी"]
    assert split_owners("राम एच. आर. शर्मा") == ["राम एच. आर. शर्मा"]  # initial with a stop never splits


def _multi_row_khatauni_ocr():
    """One page: khata + two co-owners on one line, then a 3-column table with two
    khasra rows, laid out so the "below" column-matching in parser.py lines up."""
    # columns are spaced well apart so the +-60% column-tolerance in parser.py's
    # "below" matching can't bleed a neighbouring column's token into this one
    tokens = [
        {"text": "खाता संख्या : 00245", "confidence": 0.95, "bbox": [80, 0, 320, 30]},
        {"text": "खातेदार का नाम : राम प्रसाद शर्मा एवं श्याम लाल शर्मा", "confidence": 0.9, "bbox": [80, 50, 900, 80]},
        {"text": "खसरा संख्या", "confidence": 0.95, "bbox": [80, 100, 160, 130]},
        {"text": "क्षेत्रफल", "confidence": 0.95, "bbox": [400, 100, 480, 130]},
        {"text": "भूमि का प्रकार", "confidence": 0.95, "bbox": [700, 100, 860, 130]},
        {"text": "123/1", "confidence": 0.9, "bbox": [90, 150, 150, 180]},
        {"text": "0.5", "confidence": 0.9, "bbox": [410, 150, 470, 180]},
        {"text": "कृषि (सिंचित)", "confidence": 0.9, "bbox": [710, 150, 850, 180]},
        {"text": "456/2", "confidence": 0.9, "bbox": [90, 200, 150, 230]},
        {"text": "1.2", "confidence": 0.9, "bbox": [410, 200, 470, 230]},
        {"text": "बंजर", "confidence": 0.9, "bbox": [710, 200, 780, 230]},
    ]
    lines = [
        {"bbox": [80, 0, 320, 30], "token_ids": [0]},
        {"bbox": [80, 50, 900, 80], "token_ids": [1]},
        {"bbox": [80, 100, 860, 130], "token_ids": [2, 3, 4]},
        {"bbox": [90, 150, 850, 180], "token_ids": [5, 6, 7]},
        {"bbox": [90, 200, 780, 230], "token_ids": [8, 9, 10]},
    ]
    return {"engine": "test", "languages": ["hi", "en"], "elapsed_ms": 0,
            "pages": [{"page": 1, "width": 1240, "height": 1754, "tokens": tokens, "lines": lines}]}


def test_multi_owner_and_multi_parcel_khatauni():
    ext = extract(_multi_row_khatauni_ocr())
    assert ext["owners"] == [
        {"owner_name": "राम प्रसाद शर्मा", "father_name": None},
        {"owner_name": "श्याम लाल शर्मा", "father_name": None},
    ]
    assert [p["khasra_number"] for p in ext["parcels"]] == ["123/1", "456/2"]
    assert [p["land_classification"] for p in ext["parcels"]] == ["agricultural_irrigated", "barren"]
    assert ext["parcels"][0]["plot_area_normalized"]["hectares"] == 0.5
    assert ext["parcels"][1]["plot_area_normalized"]["hectares"] == 1.2
    # single fields stay equal to the first entry
    f = {k: v["value"] for k, v in ext["fields"].items()}
    assert f["owner_name"] == "राम प्रसाद शर्मा"
    assert f["khasra_number"] == "123/1" and f["land_classification"] == "agricultural_irrigated"


def test_learning_memory_applies_corrections_and_raises_thresholds():
    mem = CorrectionMemory()
    mem.add_correction("village", "निगोह", "Nigoha")
    assert mem.lookup("village", "निगोह") == "Nigoha"
    for i in range(10):
        mem.add_review("plot_area", corrected=i < 5)
    assert mem.field_thresholds(0.8)["plot_area"] > 0.8
