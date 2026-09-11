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


def restore(words: list[str]) -> tuple[list[str], bool]:
    by_skel, latin = _index()
    out, changed = [], False
    for w in words:
        new = w
        if is_devanagari(w):
            cand = by_skel.get(skeleton(w)[0])
            if cand:
                new = cand
        elif len(w) >= 5 and w.title() not in latin:
            close = [t for t in latin if abs(len(t) - len(w)) <= 1 and Levenshtein.distance(t.lower(), w.lower()) == 1]
            if len(close) == 1:
                new = close[0]
        changed |= new != w
        out.append(new)
    return out, changed
