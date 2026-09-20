"""Finding the same parcel when the two readings of its number disagree."""
from backend.extraction.duplicates import find_duplicates, near_khasra

EXISTING = [{"record_id": 1, "district": "Lucknow", "village": "Nigohan", "khata_number": "00245",
             "khasra_number": "1805/1", "owner_name": "राम प्रसाद शर्मा"}]


def test_the_misreadings_we_actually_measured_still_match():
    """Every pair here came off the test split: one digit confused, a separator dropped, a
    Devanagari suffix lost."""
    for a, b in (("1805/1", "1305/1"), ("1501/4", "501/4"), ("1263/9क", "12639क"), ("273/6ग", "273/6")):
        ok, why = near_khasra(a, b)
        assert ok, f"{a} and {b} should be the same parcel ({why})"


def test_two_different_parcels_are_not_joined():
    assert near_khasra("123/2", "456/7")[0] is False
    assert near_khasra("1268", "1340")[0] is False


def test_a_short_number_is_not_guessed_at():
    """On a two-character number, one character apart is most of the number."""
    assert near_khasra("12", "13")[0] is False


def test_an_unrelated_character_difference_is_not_a_misreading():
    """4 and 9 are not confused by this recogniser; that is a different parcel."""
    assert near_khasra("1804/1", "1809/1")[0] is False


def test_a_near_match_alone_does_not_reach_the_threshold():
    """A near khasra is evidence, not proof. Without the khata or the owner agreeing it must
    not be enough to call two records the same."""
    record = {"district": "Lucknow", "village": "Nigohan", "khasra_number": "1305/1",
              "khata_number": "99999", "owner_name": "कोई और"}
    assert find_duplicates(record, EXISTING) == []


def test_a_near_match_with_the_khata_is_a_duplicate():
    record = {"district": "Lucknow", "village": "Nigohan", "khasra_number": "1305/1",
              "khata_number": "00245", "owner_name": "राम प्रसाद शर्मा"}
    hits = find_duplicates(record, EXISTING)
    assert hits and hits[0]["record_id"] == 1
    assert any("one character apart" in r for r in hits[0]["reasons"])


def test_a_different_village_is_never_a_duplicate():
    """The guard that stops near matching joining parcels across the state."""
    record = {"district": "Lucknow", "village": "Kakori", "khasra_number": "1805/1",
              "khata_number": "00245", "owner_name": "राम प्रसाद शर्मा"}
    assert find_duplicates(record, EXISTING) == []


def test_an_exact_match_still_scores_higher_than_a_near_one():
    exact = find_duplicates({"district": "Lucknow", "village": "Nigohan", "khasra_number": "1805/1",
                             "khata_number": "00245", "owner_name": "राम प्रसाद शर्मा"}, EXISTING)
    near = find_duplicates({"district": "Lucknow", "village": "Nigohan", "khasra_number": "1305/1",
                            "khata_number": "00245", "owner_name": "राम प्रसाद शर्मा"}, EXISTING)
    assert exact[0]["score"] > near[0]["score"]
