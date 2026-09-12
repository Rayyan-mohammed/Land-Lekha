"""Best-effort rule-based Roman -> Devanagari transliteration for Indian place names.

Used only to fill in Hindi spellings for villages pulled from the LGD directory
(see build_gazetteer.py), which publishes English names and codes but not local
script. NOT linguistically exact: whether a Roman "a"/"t"/"d" represents a long or
short vowel, or a dental or retroflex consonant, is genuinely ambiguous from the
Roman spelling alone without a pronunciation dictionary. Validated against the ~30
hand-checked village/tehsil/district names already in master/gazetteer.json: about
1 in 10 come out an exact match, most of the rest are phonetically recognisable but
not the officially correct spelling. Treat every name produced here as unverified.
"""
from __future__ import annotations

import re

VOWELS = {
    "aa": "आ", "ee": "ई", "ii": "ई", "oo": "ऊ", "uu": "ऊ",
    "ai": "ऐ", "au": "औ",
    "a": "अ", "i": "इ", "u": "उ", "e": "ए", "o": "ओ",
}
MATRAS = {
    "aa": "ा", "ee": "ी", "ii": "ी", "oo": "ू", "uu": "ू",
    "ai": "ै", "au": "ौ",
    "a": "", "i": "ि", "u": "ु", "e": "े", "o": "ो",
}
CONSONANTS = [
    ("ksh", "क्ष"), ("gy", "ज्ञ"), ("chh", "छ"), ("shh", "ष"),
    ("kh", "ख"), ("gh", "घ"), ("ch", "च"), ("jh", "झ"),
    ("th", "थ"), ("dh", "ध"), ("ph", "फ"), ("bh", "भ"),
    ("sh", "श"), ("ng", "ङ"), ("ny", "ञ"),
    ("k", "क"), ("g", "ग"), ("c", "क"), ("j", "ज"),
    ("t", "त"), ("d", "द"), ("n", "न"), ("p", "प"), ("b", "ब"),
    ("m", "म"), ("y", "य"), ("r", "र"), ("l", "ल"), ("v", "व"), ("w", "व"),
    ("s", "स"), ("h", "ह"), ("f", "फ़"), ("z", "ज़"), ("q", "क़"), ("x", "क्स"),
]
VOWEL_KEYS = sorted(VOWELS, key=len, reverse=True)
CONS_KEYS = sorted(dict(CONSONANTS), key=len, reverse=True)
CONS_MAP = dict(CONSONANTS)
DEV_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")

SUFFIX_OVERRIDES = [(re.compile(r"garh$"), "गढ़")]


def _tokenize(word: str) -> list[tuple[str, str]]:
    i, out = 0, []
    while i < len(word):
        for k in VOWEL_KEYS:
            if word[i:i + len(k)] == k:
                out.append(("V", k)); i += len(k); break
        else:
            for k in CONS_KEYS:
                if word[i:i + len(k)] == k:
                    out.append(("C", k)); i += len(k); break
            else:
                # a digit or punctuation mark: keep it literally instead of dropping it, so
                # e.g. "Chak No.7" and "Chak No.12" stay distinct instead of colliding once
                # both become "chak no"
                out.append(("L", word[i]))
                i += 1
    return out


def _word_to_devanagari(word: str) -> str:
    w = word.lower()
    for pat, repl in SUFFIX_OVERRIDES:
        m = pat.search(w)
        if m:
            prefix = _word_to_devanagari(w[:m.start()]) if m.start() else ""
            return prefix + repl
    toks = _tokenize(w)
    n = len(toks)
    result = []
    i = 0
    while i < n:
        kind, val = toks[i]
        if kind == "L":
            result.append(val.translate(DEV_DIGITS))
            i += 1
            continue
        if kind == "V":
            result.append(VOWELS[val])
            i += 1
            continue
        cons_dev = CONS_MAP[val]
        nxt = toks[i + 1] if i + 1 < n else None
        if nxt and nxt[0] == "V":
            vowel = nxt[1]
            is_last_pair = i + 2 == n
            matra = "ा" if vowel == "a" and not is_last_pair else MATRAS[vowel]
            result.append(cons_dev + matra)
            i += 2
        else:
            result.append(cons_dev if i == n - 1 else cons_dev + "्")
            i += 1
    return "".join(result)


def to_devanagari(name: str) -> str:
    return " ".join(_word_to_devanagari(w) for w in name.split())
