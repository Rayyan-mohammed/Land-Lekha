"""Dictionary-based post-OCR correction for person names.

Only fixes what OCR reliably breaks without changing the name itself:
  * Devanagari: restores dropped anusvara / halant / nukta when the letter skeleton
    matches a known token exactly (सिह -> सिंह, चंदर -> चंद्र)
  * Latin: one-character slips in names of 5+ letters when exactly one known token
    is that close (Kamnla -> Kamla)
Unknown names pass through untouched.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from .normalize import is_devanagari, skeleton

LEXICON = Path(__file__).parent / "master" / "name_tokens.json"


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, str | None], list[str]]:
    tokens = json.loads(LEXICON.read_text(encoding="utf-8"))["tokens"]
    by_skel: dict[str, str | None] = {}
    for hi, _ in tokens:
        sk = skeleton(hi)[0]
        by_skel[sk] = None if sk in by_skel and by_skel[sk] != hi else hi  # None = ambiguous
    latin = sorted({en for _, en in tokens})
    return by_skel, latin


# Letter confusions OCR makes in Devanagari names, as skeleton substitutions (bad -> good):
# व read as च (यादव -> यादच), थ as य (नाथ -> नाय), the conjunct ंद्र as ट (नरेंद्र -> नरेट; the
# skeleton drops ं and ्, so ंद्र is "दर" there), वर् as च (वर्मा -> च्मा), अ as भ (अशोक -> भशोक)
# and क as झ (कमला -> झमला).
_CONFUSIONS = (("च", "व"), ("य", "थ"), ("ट", "दर"), ("च", "वर"), ("भ", "अ"), ("झ", "क"))


def _confusion_match(sk: str, by_skel: dict[str, str | None]) -> str | None:
    """A known token reachable from `sk` by undoing OCR confusions, if exactly one is."""
    found = set()
    for bad, good in _CONFUSIONS:
        variants = {sk.replace(bad, good)}  # every occurrence at once
        i = sk.find(bad)
        while i != -1:  # and each occurrence on its own
            variants.add(sk[:i] + good + sk[i + len(bad):])
            i = sk.find(bad, i + 1)
        found |= {by_skel[v] for v in variants if v != sk and by_skel.get(v)}
    return found.pop() if len(found) == 1 else None


def restore(words: list[str]) -> tuple[list[str], bool]:
    by_skel, latin = _index()
    out, changed = [], False
    for w in words:
        new = w
        if is_devanagari(w):
            sk = skeleton(w)[0]
            cand = by_skel.get(sk)
            if cand:
                new = cand
            elif sk not in by_skel:  # unknown (not ambiguous): try undoing OCR letter confusions
                new = _confusion_match(sk, by_skel) or w
        elif len(w) >= 5 and w.title() not in latin:
            close = [t for t in latin if abs(len(t) - len(w)) <= 1 and Levenshtein.distance(t.lower(), w.lower()) == 1]
            if len(close) == 1:
                new = close[0]
        changed |= new != w
        out.append(new)
    return out, changed
