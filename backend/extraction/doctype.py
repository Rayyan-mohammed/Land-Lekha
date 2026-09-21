"""What kind of land record is this page?

One implementation, in extraction, where the rest of the reading of a page lives. It replaces
both the six-entry list that was here before and the parallel list that sat in the removed
land/non-land classifier.

This is not a gate. It never decides whether a page should be processed - it names what was
read, for the repository and for the verifier, and says "unknown" without apology when the
title is one it does not know. An unknown type is still extracted from.

The same record wears a different name in every state: a UP Khatauni, a Rajasthan Jamabandi
and a Telangana Pahani are all the Record of Rights. Two of those names on one page is not
ambiguity, so the regional name is kept and the family reported beside it.
"""
from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

HEAD_LINES = 3     # a document names itself at the top
HEAD_CHARS = 300   # ...and a title is never longer than this, however long those lines are

TYPES: dict[str, list[str]] = {
    "sale_deed": ["sale deed", "vendor", "vendee", "consideration", "विक्रय पत्र", "बैनामा", "deed of sale", "sale-deed", "विक्रय विलेख", "విక్రయ పత్రము", "విక్రయ దస్తావేజు"],
    "gift_deed": ["gift deed", "donor", "donee", "दान पत्र", "deed of gift", "gift-deed", "दानपत्र", "హిబా", "దాన పత్రము"],
    "lease_deed": ["lease deed", "lessor", "lessee", "lease period", "पट्टा विलेख", "deed of lease", "lease-deed", "पट्टानामा", "पट्टा नामा", "कौल पत्र", "కౌలు పత్రము"],
    "exchange_deed": ["exchange deed", "विनिमय पत्र", "deed of exchange"],
    "partition_deed": ["partition deed", "विभाजन पत्र", "बंटवारा", "deed of partition"],
    "mortgage": ["mortgage deed", "mortgagor", "mortgagee", "बंधक पत्र", "deed of mortgage"],
    "will": ["testator", "bequeath", "वसीयत"],
    "mutation": ["mutation", "mutation no", "नामांतरण", "दाखिल खारिज"],
    "pahani_adangal": ["pahani", "adangal", "village account", "పహాణి", "ఆదంగల్"],
    "patta": ["patta passbook", "pattadar passbook", "patta chitta", "पट्टा पासबुक",
              "పట్టాదారు పాస్ పుస్తకం"],
    "jamabandi": ["jamabandi", "जमाबंदी"],
    "khatauni": ["khatauni", "खतौनी"],
    "khatiyan": ["khatiyan", "खतियान"],
    "record_of_rights": ["record of rights", "rtc", "अधिकार अभिलेख"],
    "khasra": ["khasra panchsala", "khasra record", "khasra girdawari", "खसरा पांचसाला",
               "खसरा गिरदावरी"],
    "survey_record": ["survey record", "survey settlement", "भूमि सर्वेक्षण"],
    "land_register": ["land register", "भू अभिलेख रजिस्टर"],
    "registration_document": ["sub registrar", "registration no", "उप निबंधक", "पंजीकरण संख्या"],
    "land_allotment": ["allotment", "land grant", "आवंटन", "भूमि अनुदान"],
    "naksha": ["naksha", "cadastral map", "shajra", "नक्शा", "मानचित्र"],
    "particulars_form": ["particulars form", "विवरण प्रपत्र"],
}

FAMILY: dict[str, str] = {
    "khatauni": "record_of_rights", "jamabandi": "record_of_rights", "khatiyan": "record_of_rights",
    "pahani_adangal": "record_of_rights", "patta": "record_of_rights",
    "record_of_rights": "record_of_rights",
    "sale_deed": "registered_deed", "gift_deed": "registered_deed", "lease_deed": "registered_deed",
    "exchange_deed": "registered_deed", "partition_deed": "registered_deed",
    "mortgage": "registered_deed", "registration_document": "registered_deed",
    "naksha": "map", "khasra": "khasra", "survey_record": "survey",
}


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text.lower())
    return re.sub(r"[^\w\u0900-\u0DFF\u0600-\u06FF]+", " ", text)


def _matches(term: str, head: str) -> bool:
    """OCR bends a title: खतौनी comes back as खतोनी, one vowel sign out. Compare the consonant
    skeleton for Devanagari, as the extractor does for labels, and a fuzzy ratio otherwise."""
    t = _normalise(term)
    if t in head:
        return True
    if any("ऀ" <= ch <= "ॿ" for ch in t):
        from .normalize import skeleton
        # whole words only: a short consonant skeleton turns up inside garbled text by chance
        return f" {skeleton(t)[0]} " in f" {skeleton(head)[0]} "
    return fuzz.partial_ratio(t, head) >= 88


def identify(text: str) -> dict:
    """Name the document from its text. Always answers; "unknown" is a real answer."""
    hay = _normalise(text)
    # The title block, by line - not by character count. A short page is barely 250 characters
    # all told, and a fixed character window swallowed the body of it: a Khatauni whose last
    # line mentioned a mutation number came back as a mutation record.
    head = _normalise(chr(10).join(text.splitlines()[:HEAD_LINES]))[:HEAD_CHARS]
    scores: dict[str, float] = {}
    for name, terms in TYPES.items():
        # one piece of evidence per distinct title: "sale deed" and "sale-deed" normalise to
        # the same string, and a type must not outscore another for having more spellings
        terms = list(dict.fromkeys(_normalise(t).strip() for t in terms))
        in_head = sum(1 for t in terms if _matches(t, head))
        in_body = sum(1 for t in terms if t in hay)
        score = 3.0 * in_head + max(0, in_body - in_head)
        if score:
            scores[name] = score
    if not scores:
        return {"type": "unknown", "family": None, "confidence": 0.0, "also_seen": []}

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    best, best_score = ranked[0]
    contenders = [n for n, sc in ranked if sc >= best_score * 0.9]
    also = [n for n in contenders[1:] if FAMILY.get(n) != FAMILY.get(best) or not FAMILY.get(best)]
    # a Khatauni page that also says "Record of Rights" is one document, not two candidates
    confident = len(also) == 0
    return {
        "type": best,
        "family": FAMILY.get(best),
        "confidence": round(min(0.95, 0.5 + 0.12 * best_score) if confident else 0.4, 4),
        "also_seen": also[:3],
    }
