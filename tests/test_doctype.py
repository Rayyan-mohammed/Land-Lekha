"""Naming the document. Not a gate - "unknown" is a real answer and never stops anything."""
from backend.extraction.doctype import identify


def test_a_khatauni_that_also_says_record_of_rights_is_one_document():
    """Both titles are on the page because a UP Khatauni *is* the Record of Rights. That is
    not two candidates; keep the regional name and report the family."""
    r = identify("खतौनी (अधिकार अभिलेख)\nग्राम : निगोहाँ\nखाता संख्या : 00245")
    assert r["type"] == "khatauni" and r["family"] == "record_of_rights"
    assert r["also_seen"] == [] and r["confidence"] > 0.5


def test_a_body_mention_does_not_outrank_the_title():
    """A Khatauni whose last line carries a mutation number is still a Khatauni. A fixed
    character window used to swallow the whole of a short page and answer "mutation"."""
    r = identify("खतौनी (अधिकार अभिलेख)\nखाता संख्या : 00245\nखसरा संख्या : 123/2\n"
                 "नामांतरण संख्या : 4521   नामांतरण दिनांक : 12/03/2019")
    assert r["type"] == "khatauni"


def test_a_deed_is_named_from_its_parties():
    r = identify("GIFT DEED\nexecuted by donor Ram Prasad in favour of donee Shyam Lal\nsurvey no 142/2")
    assert r["type"] == "gift_deed" and r["family"] == "registered_deed"


def test_a_pahani_and_an_adangal_are_the_same_record_under_two_names():
    assert identify("పహాణి\nSurvey No 142/2")["type"] == "pahani_adangal"
    assert identify("Adangal\nSurvey No 142/2")["type"] == "pahani_adangal"


def test_an_unknown_title_is_answered_not_refused():
    r = identify("Some page with a heading we have never seen\nand a few numbers 123")
    assert r["type"] == "unknown" and r["family"] is None and r["confidence"] == 0.0


def test_two_unrelated_titles_lower_the_confidence():
    """A page that reads as both a sale deed and a naksha is not something to be sure about."""
    r = identify("SALE DEED cadastral map naksha\nvendor and vendee\nshajra")
    assert r["confidence"] <= 0.5 and r["also_seen"]


def test_a_misread_title_still_lands():
    """OCR bends खतौनी into खतोनी, one vowel sign out."""
    assert identify("खतोनी\nग्राम : निगोहाँ")["type"] == "khatauni"
