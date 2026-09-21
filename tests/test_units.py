"""Every area unit the vocabulary knows has to convert. Two did not, and one was silently wrong."""
import pytest

from backend.extraction.labels import AREA_UNIT_WORDS
from backend.extraction.validate import HECTARES_PER, parse_area


def test_every_unit_the_vocabulary_can_return_converts():
    """Gunta and cent were added to the vocabulary for Telugu records without a row in the
    conversion table, and any page mentioning them crashed extraction with KeyError."""
    missing = [u for u in AREA_UNIT_WORDS if u not in HECTARES_PER and u != "bigha"]
    assert missing == [], f"units with no conversion: {missing}"


@pytest.mark.parametrize("text,unit,hectares", [
    ("26.5856 Cents", "cent", 0.1076),      # a West Bengal gift deed
    ("2 గుంటలు", "gunta", 0.0202),           # Telangana
    ("1.25 ఎకరం", "acre", 0.5059),
    ("0.412 हेक्टेयर", "hectare", 0.412),
])
def test_units_convert_to_hectares(text, unit, hectares):
    n = parse_area(text).normalized
    assert n["unit"] == unit and abs(n["hectares"] - hectares) < 1e-3


def test_kanal_and_marla_are_one_area_not_a_hectare():
    """"8 कनाल 16 मरला" used to read as 8 hectares - twenty times too big - because kanal was
    not a unit it knew, so it fell back to assuming hectare."""
    for text in ("8 कनाल 16 मरला", "8 kanal 16 marla"):
        n = parse_area(text).normalized
        assert n["unit"] == "kanal" and n["value"] == 8.8
        assert abs(n["hectares"] - 0.4452) < 1e-3


def test_eight_kanal_is_one_acre():
    assert abs(8 * HECTARES_PER["kanal"] - HECTARES_PER["acre"]) < 0.001


def test_a_unit_with_no_conversion_is_flagged_not_fatal(monkeypatch):
    import backend.extraction.validate as v

    monkeypatch.setattr(v, "find_unit", lambda text: "biswa")
    p = v.parse_area("4 biswa")
    assert p.value and p.normalized["hectares"] is None
    assert any("no conversion" in i for i in p.issues) and p.rule_score < 0.5
