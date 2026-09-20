"""Script detection: what writing systems are on the page, and which reader can read them."""
from backend.ocr.scripts import detect_scripts, readers_for, script_of, script_shares

HINDI = "खतौनी ग्राम निगोहाँ खसरा संख्या"
TELUGU = "పహాణీ అడంగల్ విస్తీర్ణం సర్వే"


def test_a_bilingual_land_record_reports_both_scripts():
    """Which one leads depends on how much of each is on the page: a bilingual form with
    English labels is often more Latin than Devanagari, and saying so is correct."""
    text = HINDI + " Khata 00245 hectare"
    assert set(detect_scripts(text)) == {"Devanagari", "Latin"}
    codes, missing = readers_for(detect_scripts(text))
    assert set(codes) == {"hi", "en"} and missing == []


def test_a_telugu_page_asks_for_the_telugu_reader():
    text = TELUGU + " No 142/2"
    assert detect_scripts(text)[0] == "Telugu"
    codes, missing = readers_for(detect_scripts(text))
    assert set(codes) == {"te", "en"} and missing == []


def test_a_script_we_cannot_read_is_named_rather_than_ignored():
    """Saying "there is Malayalam here and we have no reader for it" beats silence."""
    codes, missing = readers_for(["Malayalam", "Latin"])
    assert missing == ["Malayalam"] and codes == ["en"]


def test_latin_is_always_read_because_the_numbers_are_latin():
    codes, _ = readers_for(["Devanagari"])
    assert "en" in codes


def test_a_stray_character_is_not_a_language_on_the_page():
    """One Tamil letter in a page of Hindi is a misread, not a second language."""
    text = HINDI * 20 + " அ"
    assert "Tamil" not in detect_scripts(text)
    assert script_shares(text)["Devanagari"] > 0.9


def test_digits_and_punctuation_are_not_letters():
    assert script_of("7") is None and script_of("/") is None and script_of("०") is None


def test_a_page_with_no_letters_has_no_scripts():
    assert detect_scripts("123 / 456 . 789") == []
