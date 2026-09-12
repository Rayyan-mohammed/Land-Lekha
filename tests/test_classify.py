"""Is it a land record at all? Decided from several kinds of evidence, never one word."""
from backend.classify import classify, detect_scripts

KHATAUNI = ("उत्तर प्रदेश सरकार खतौनी अधिकार अभिलेख ग्राम निगोहाँ तहसील मोहनलालगंज जिला लखनऊ "
            "खाता संख्या 00245 खसरा संख्या 123/2 क्षेत्रफल 0.412 हेक्टेयर खातेदार राम प्रसाद शर्मा")
GIFT_DEED = ("GIFT DEED. This deed of gift executed by the donor Ram Prasad in favour of the donee Shyam Lal. "
             "Survey No. 142/2, extent 0.50 acre, bounded on the east by the road and on the west by plot 12. "
             "Registered with the Sub Registrar, Lucknow, registration no 1996/40440. Tehsil Sadar.")
PAHANI = "పహాణి Survey No 142/2 Pattadar విస్తీర్ణం 2 ఎకరం Mandal Revenue Office village Pokhra"
INVOICE = "TAX INVOICE  Acme Traders  GSTIN 07AABCU9603R1ZM  Steel pipes 12 x 450.00  Total due Rs 16,800  Payment terms 30 days"
MARKSHEET = "Board of Secondary Education  Certificate  Roll No 123456  Examination March 2019  Grade A  University"
GOVT_HEALTH = "Government of India  Ministry of Health  Certificate of vaccination  issued at District Hospital  Collector's seal"


def test_a_khatauni_is_a_land_record_and_says_so():
    r = classify(KHATAUNI, tokens=60)
    assert r["is_land_document"] is True and r["confidence"] >= 0.8
    assert r["evidence_kinds"] >= 3
    assert r["document_type"] == "khatauni" and r["type_family"] == "record_of_rights"
    assert r["scripts"] == ["Devanagari"]


def test_a_gift_deed_is_typed_from_its_own_words():
    r = classify(GIFT_DEED, tokens=80)
    assert r["is_land_document"] is True
    assert r["document_type"] == "gift_deed" and r["type_family"] == "registered_deed"
    assert r["scripts"] == ["Latin"]


def test_telugu_pahani_is_recognised_with_its_scripts():
    r = classify(PAHANI, tokens=40)
    assert r["is_land_document"] is True and r["document_type"] == "pahani_adangal"
    assert set(r["scripts"]) == {"Telugu", "Latin"}


def test_an_invoice_a_marksheet_and_a_health_certificate_are_not_land_records():
    for text in (INVOICE, MARKSHEET, GOVT_HEALTH):
        r = classify(text, tokens=40)
        assert r["is_land_document"] is False, text[:30]
        assert r["confidence"] >= 0.8
        assert r["document_type"] is None


def test_a_government_seal_does_not_make_a_land_record():
    """Part 26: 'Government' on the page, a seal, a person's name, a number - none is evidence."""
    r = classify(GOVT_HEALTH, tokens=40)
    assert r["government_indicators"]                    # noticed, and said out loud
    assert r["is_land_document"] is False                # but not credited


def test_one_kind_of_evidence_is_never_enough():
    """'survey' alone, or 'area' alone, is on every second form in the country."""
    assert classify("please complete the survey no later than Friday and return it", tokens=30)["is_land_document"] is False
    assert classify("the total area of the hall is 400 square metre, hectare rates apply", tokens=30)["is_land_document"] is False


def test_a_land_record_of_unknown_type_goes_forward_not_out():
    r = classify("Bhoomi abhilekh village Pokhra tehsil Sadar khata 00646 khasra 12/3 area 1.2 hectare owner Pushpa Tiwari",
                 tokens=40)
    assert r["is_land_document"] is True
    assert r["document_type"] == "unknown"
    assert "look at it" in r["reason"]


def test_an_unreadable_page_is_undetermined_not_rejected():
    """A poor photo goes back for a retake; noise read off it must not become 'not a land document'."""
    r = classify("f9 ;: xq  wz", tokens=3)
    assert r["is_land_document"] is None and r["undetermined"] is True
    r = classify(INVOICE, tokens=40, quality="poor")
    assert r["is_land_document"] is None and r["undetermined"] is True


def test_scripts_are_detected_not_translated():
    assert detect_scripts("Government of Telangana పహాణి") == ["Latin", "Telugu"] or            detect_scripts("Government of Telangana పహాణి") == ["Telugu", "Latin"]
    assert detect_scripts("1234 / 5") == []
