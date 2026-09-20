"""Telugu: the labels a Pahani or Adangal uses, and the units it measures land in.

The reading itself is measured in eval/results/telugu.md - this holds the vocabulary in
place so a change to the alias table cannot silently drop a script.
"""
from backend.extraction.extractor import extract
from backend.extraction.labels import ALIAS_INDEX, AREA_UNIT_WORDS
from backend.extraction.normalize import label_key


def _ocr(lines):
    tokens, out = [], []
    for i, (text, conf) in enumerate(lines):
        y = 100 + i * 50
        box = [80, y, 80 + 20 * len(text), y + 30]
        tokens.append({"text": text, "confidence": conf, "bbox": box})
        out.append({"text": text, "confidence": conf, "bbox": box, "token_ids": [i]})
    return {"engine": "test", "languages": ["te", "en"], "elapsed_ms": 0,
            "pages": [{"page": 1, "width": 1240, "height": 700, "tokens": tokens, "lines": out}]}


def test_a_telugu_pahani_gives_up_its_fields():
    ext = extract(_ocr([
        ("పహాణీ / ADANGAL", 0.78),
        ("గ్రామం : కొత్తపల్లి    మండలం : ఇబ్రహీంపట్నం", 0.7),
        ("జిల్లా : రంగారెడ్డి    రాష్ట్రం : తెలంగాణ", 0.8),
        ("పట్టాదారు పేరు : రమేష్ కుమార్", 0.75),
        ("ఖాతా సంఖ్య : 00412", 0.9),
        ("సర్వే నంబరు : 142/2", 0.9),
        ("విస్తీర్ణం : 1.25 ఎకరం", 0.8),
    ]))
    f = {k: v["value"] for k, v in ext["fields"].items() if v.get("value")}
    assert ext["document_type"] == "pahani_adangal"
    assert f["khata_number"] == "00412"
    assert f["survey_number"] == "142/2"
    assert f["owner_name"] == "రమేష్ కుమార్"          # kept as written, never translated
    assert ext["fields"]["plot_area"]["normalized"]["unit"] == "acre"


def test_a_mandal_is_the_tehsil_field_not_a_new_one():
    """The same administrative level, under the name the state uses for it."""
    ext = extract(_ocr([("మండలం : ఇబ్రహీంపట్నం", 0.9), ("జిల్లా : రంగారెడ్డి", 0.9)]))
    assert ext["fields"]["tehsil"]["value"]
    assert ext["fields"]["district"]["value"]


def test_telugu_land_units_are_known():
    for unit, word in (("acre", "ఎకరం"), ("gunta", "గుంట"), ("cent", "సెంట్లు"), ("hectare", "హెక్టారు")):
        assert word in AREA_UNIT_WORDS[unit], f"{word} missing from {unit}"


def test_every_field_that_a_pahani_carries_has_a_telugu_alias():
    """If someone adds a field and forgets the Telugu label, a Telugu page silently loses it."""
    by_field: dict[str, list[str]] = {}
    for field, alias, _ in ALIAS_INDEX:
        by_field.setdefault(field, []).append(alias)
    on_a_pahani = ["owner_name", "father_name", "khata_number", "survey_number", "plot_area",
                   "land_classification", "village", "tehsil", "district", "state"]
    missing = [f for f in on_a_pahani
               if not any(any("\u0c00" <= ch <= "\u0c7f" for ch in a) for a in by_field.get(f, []))]
    assert missing == [], f"no Telugu label for: {missing}"


def test_a_telugu_label_normalises_to_something_matchable():
    assert label_key("సర్వే నంబరు") and label_key("ఖాతా సంఖ్య")
