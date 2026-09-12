"""Land-document classification from OCR text and page geometry.

How it decides, and what it refuses to do:

* **Never one keyword.** A page scores by how many *different kinds* of land evidence it
  carries - a parcel identifier, an extent, a revenue office, a tenure word, boundaries, a
  transaction. One group alone is never enough, however often its words appear, because
  "survey" appears on school forms and "area" appears on everything.
* **Evidence against counts too.** Invoice, certificate, bank, newspaper and identity
  vocabulary pushes the score down, so a government marksheet does not become a land record
  by having a seal on it.
* **Government indicators are reported, not credited.** "Revenue Department" on the page is
  worth saying out loud; it is not evidence of authenticity and barely moves the score.
* **Unknown type is not rejection.** A page can be clearly a land record and match no type we
  know; it goes forward for generic extraction, flagged for a person to look at.

The confidence is the model's own quantity - the weighted evidence balance squashed to 0..1 -
not a number chosen to look good. It is a rule ensemble, not a trained network: honest about
what it is, and measured in eval/classify_eval.py.
"""
from __future__ import annotations

import math
import os
import re
import unicodedata

from rapidfuzz import fuzz

from .vocabulary import GOVERNMENT, LAND_GROUPS, NOT_LAND

MIN_GROUPS = int(os.getenv("LL_CLASSIFY_MIN_GROUPS", "2"))
MIN_WORDS_TO_JUDGE = int(os.getenv("LL_CLASSIFY_MIN_WORDS", "12"))  # fewer words read: cannot say either way
LAND_THRESHOLD = float(os.getenv("LL_CLASSIFY_THRESHOLD", "0.5"))
TYPE_MARGIN = float(os.getenv("LL_CLASSIFY_TYPE_MARGIN", "1.5"))

DOCUMENT_TYPES: dict[str, list[str]] = {
    "sale_deed": ["sale deed", "vendor", "vendee", "consideration"],
    "gift_deed": ["gift deed", "donor", "donee"],
    "lease_deed": ["lease deed", "lessor", "lessee", "lease period"],
    "exchange_deed": ["exchange deed"],
    "partition_deed": ["partition deed"],
    "mortgage": ["mortgage deed", "mortgagor", "mortgagee"],
    "will": ["testator", "bequeath"],
    "mutation": ["mutation", "mutation no"],
    "pahani_adangal": ["pahani", "adangal", "village account"],  # one record, two names (TS/AP and TN)
    "patta": ["patta passbook", "pattadar passbook", "patta chitta"],
    "jamabandi": ["jamabandi"],
    "khatauni": ["khatauni"],
    "khatiyan": ["khatiyan"],
    "record_of_rights": ["record of rights", "rtc"],
    "khasra": ["khasra panchsala", "khasra record", "khasra girdawari"],
    "survey_record": ["survey record", "survey settlement"],
    "land_register": ["land register"],
    "registration_document": ["sub registrar", "registration no"],
    "land_allotment": ["allotment", "land grant"],
    "naksha": ["naksha", "cadastral map", "shajra"],
    "particulars_form": ["particulars form"],
}

DOCUMENT_TYPES_HI: dict[str, list[str]] = {
    "sale_deed": ["विक्रय पत्र", "बैनामा"],
    "gift_deed": ["दान पत्र"],
    "lease_deed": ["पट्टा विलेख"],
    "exchange_deed": ["विनिमय पत्र"],
    "partition_deed": ["विभाजन पत्र", "बंटवारा"],
    "mortgage": ["बंधक पत्र"],
    "will": ["वसीयत"],
    "mutation": ["नामांतरण", "दाखिल खारिज"],
    "pahani_adangal": ["పహాణి", "ఆదంగల్"],
    "patta": ["पट्टा पासबुक", "పట్టాదారు పాస్ పుస్తకం"],
    "jamabandi": ["जमाबंदी"],
    "khatauni": ["खतौनी"],
    "khatiyan": ["खतियान"],
    "record_of_rights": ["अधिकार अभिलेख"],
    "khasra": ["खसरा पांचसाला", "खसरा गिरदावरी"],
    "survey_record": ["भूमि सर्वेक्षण"],
    "land_register": ["भू अभिलेख रजिस्टर"],
    "registration_document": ["उप निबंधक", "पंजीकरण संख्या"],
    "land_allotment": ["आवंटन", "भूमि अनुदान"],
    "naksha": ["नक्शा", "मानचित्र"],
    "particulars_form": ["विवरण प्रपत्र"],
}

_SCRIPTS = [
    ("Devanagari", 0x0900, 0x097F), ("Bengali", 0x0980, 0x09FF), ("Gurmukhi", 0x0A00, 0x0A7F),
    ("Gujarati", 0x0A80, 0x0AFF), ("Oriya", 0x0B00, 0x0B7F), ("Tamil", 0x0B80, 0x0BFF),
    ("Telugu", 0x0C00, 0x0C7F), ("Kannada", 0x0C80, 0x0CFF), ("Malayalam", 0x0D00, 0x0D7F),
    ("Arabic", 0x0600, 0x06FF),
]


def detect_scripts(text: str, min_share: float = 0.04) -> list[str]:
    """Which writing systems are actually on the page, by share of its letters.

    Script, not language: Hindi and Marathi are both Devanagari, and saying so is honest.
    The original text is never translated or rewritten."""
    counts: dict[str, int] = {}
    letters = 0
    for ch in text:
        if not ch.isalpha():
            continue
        letters += 1
        code = ord(ch)
        if code < 0x0250:
            counts["Latin"] = counts.get("Latin", 0) + 1
            continue
        for name, lo, hi in _SCRIPTS:
            if lo <= code <= hi:
                counts[name] = counts.get(name, 0) + 1
                break
    if not letters:
        return []
    return [n for n, c in sorted(counts.items(), key=lambda kv: -kv[1]) if c / letters >= min_share]


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text.lower())
    return re.sub(r"[^\w\u0900-\u0DFF\u0600-\u06FF]+", " ", text)


def _hits(hay: str, terms: list[str]) -> list[str]:
    return [t for t in terms if _normalise(t) in hay]


HEAD_CHARS = 220  # roughly the title block; a type named there is worth three body mentions

# The same record wears a different name in each state. A UP Khatauni *is* the Record of
# Rights, and its title says both; a Jamabandi is Rajasthan's, a Pahani is Telangana's. When
# two titles on one page belong to one family, that is not ambiguity - keep the regional name
# and say which family it belongs to.
FAMILY: dict[str, str] = {
    "khatauni": "record_of_rights", "jamabandi": "record_of_rights", "khatiyan": "record_of_rights",
    "pahani_adangal": "record_of_rights", "patta": "record_of_rights", "record_of_rights": "record_of_rights",
    "sale_deed": "registered_deed", "gift_deed": "registered_deed", "lease_deed": "registered_deed",
    "exchange_deed": "registered_deed", "partition_deed": "registered_deed", "mortgage": "registered_deed",
    "registration_document": "registered_deed",
    "naksha": "map", "khasra": "khasra", "survey_record": "survey",
}


def _title_match(term: str, head: str) -> bool:
    """OCR bends a title: खतौनी comes back as खतोनी, a vowel sign off. Compare the consonant
    skeleton for Devanagari (as the extractor does for labels), a fuzzy ratio for the rest."""
    t = _normalise(term)
    if t in head:
        return True
    if any("ऀ" <= ch <= "ॿ" for ch in t):
        # whole words only: a four-consonant skeleton turns up inside garbled text by chance
        from backend.extraction.normalize import skeleton
        return f" {skeleton(t)[0]} " in f" {skeleton(head)[0]}"
    return fuzz.partial_ratio(t, head) >= 88


def _type_scores(hay: str) -> dict[str, float]:
    """A document says what it is at the top. "khasra" in the body is a field label on almost
    every land page; "khasra panchsala" in the title is the document's name."""
    head = hay[:HEAD_CHARS]
    scores = {}
    for name, terms in DOCUMENT_TYPES.items():
        all_terms = terms + DOCUMENT_TYPES_HI.get(name, [])
        in_head = sum(1 for t in all_terms if _title_match(t, head))
        in_body = len(_hits(hay, all_terms))
        scores[name] = 3.0 * in_head + 1.0 * max(0, in_body - in_head)
    return scores


def classify(text: str, *, words: int | None = None, quality: str | None = None) -> dict:
    """Decide whether this page is a land record, and what kind.

    `text` is the OCR text of the whole document, exactly as read - never a template."""
    hay = _normalise(text)
    # A page the quality check calls poor is already going back for a retake; what little was
    # read from it is noise, and noise must not be turned into "not a land document".
    if words is None:
        words = len(text.split())
    if words < MIN_WORDS_TO_JUDGE or quality == "poor":
        # nothing legible was read - that is a quality problem, not a verdict on the document
        return {"is_land_document": None, "undetermined": True, "confidence": 0.0, "evidence": {},
                "evidence_kinds": 0, "evidence_against": {}, "government_indicators": [],
                "scripts": detect_scripts(text), "words": words, "document_type": None,
                "document_type_confidence": 0.0,
                "reason": "too little was read from this page to say what it is"}
    groups = {name: _hits(hay, terms) for name, terms in LAND_GROUPS.items()}
    present = {name: found for name, found in groups.items() if found}
    against = {kind: found for kind, terms in NOT_LAND.items() if (found := _hits(hay, terms))}
    government = _hits(hay, GOVERNMENT)

    for_score = sum(1.0 + 0.25 * min(len(found) - 1, 4) for found in present.values())
    against_score = sum(1.0 + 0.5 * min(len(found) - 1, 3) for found in against.values())
    balance = for_score - 1.6 * against_score + 0.15 * bool(government)
    # centred so that two kinds of evidence with nothing against them lean *towards* land:
    # wrongly calling a real record "not a land document" is the worse mistake, since a
    # wrongly passed page only goes to a verifier
    confidence = 1 / (1 + math.exp(-(balance - 1.8)))

    enough_kinds = len(present) >= MIN_GROUPS
    is_land = bool(enough_kinds and confidence >= LAND_THRESHOLD)
    if not enough_kinds:
        confidence = min(confidence, 0.45)

    result = {
        "is_land_document": is_land,
        "confidence": round(float(confidence if is_land else 1 - confidence), 4),
        "evidence": {name: found[:6] for name, found in present.items()},
        "evidence_kinds": len(present),
        "evidence_against": {k: v[:4] for k, v in against.items()},
        "government_indicators": government[:6],
        "scripts": detect_scripts(text),
        "words": words,
        "document_type": None,
        "document_type_confidence": 0.0,
        "reason": "",
        "undetermined": False,
    }
    if not is_land:
        result["reason"] = (
            "no land-record evidence on the page" if not present
            else f"only one kind of land evidence ({', '.join(present)})" if not enough_kinds
            else f"reads like {', '.join(against)} rather than a land record" if against
            else f"land evidence is weak ({', '.join(present)})")
        return result

    ranked = sorted(_type_scores(hay).items(), key=lambda kv: -kv[1])
    best, best_n = ranked[0]
    contenders = [name for name, n in ranked[1:] if n and n * TYPE_MARGIN > best_n]
    same_family = all(FAMILY.get(c) == FAMILY.get(best) and FAMILY.get(best) for c in contenders)
    result["type_candidates"] = [name for name, n in ranked[:3] if n]
    result["type_family"] = FAMILY.get(best) if best_n else None
    if best_n == 0:
        result["document_type"] = "unknown"
        result["reason"] = "a land record, but its type is not one we recognise - please look at it"
    elif contenders and not same_family:
        result["document_type"] = "unknown"
        result["reason"] = f"a land record that could be {' or '.join([best] + contenders)} - please look at it"
    else:
        if contenders:
            # "Khatauni (Record of Rights)": the regional name beats the family name - but only
            # when its title is actually on the page. Two regional names both matched loosely
            # means we cannot tell which state's record this is, so say the family instead.
            head = hay[:HEAD_CHARS]
            exact = [n for n in [best] + contenders
                     if n != FAMILY.get(n) and any(_normalise(t) in head for t in DOCUMENT_TYPES[n] + DOCUMENT_TYPES_HI.get(n, []))]
            regional = [n for n in [best] + contenders if n != FAMILY.get(n)]
            best = exact[0] if len(exact) == 1 else (regional[0] if len(regional) == 1 else FAMILY[best])
        result["document_type"] = best
        result["document_type_confidence"] = round(min(0.95, 0.45 + 0.15 * best_n), 4)
        result["reason"] = f"{len(present)} kinds of land evidence on the page"
    return result
