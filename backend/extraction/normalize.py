"""Text normalisation helpers for mixed Hindi / English OCR output."""
from __future__ import annotations

import re
import unicodedata

DEV_TO_ASCII = str.maketrans("०१२३४५६७८९", "0123456789")
ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"), None)

# common OCR confusions inside numbers
_DIGIT_LOOKALIKE = str.maketrans({"O": "0", "o": "0", "D": "0", "I": "1", "l": "1", "L": "1", "|": "1", "!": "1",
                                  "Z": "2", "z": "2", "S": "5", "s": "5", "$": "5", "G": "6", "T": "7", "B": "8",
                                  "g": "9", "q": "9"})
# Matching skeleton: marks the recogniser often drops or confuses on degraded scans
_SKEL_DROP = set("ंँ़्ःऽ")
_SKEL_MAP = {"ी": "ि", "ू": "ु", "ौ": "ो", "ै": "े", "ख": "स", "ई": "इ", "ऊ": "उ", "ण": "न", "ढ": "ड", "ॉ": "ो",
             "ब": "व"}


def skeleton(text: str) -> tuple[str, list[int]]:
    """Lower-cased, mark-stripped form of `text` for fuzzy label matching, plus a map
    from each skeleton character back to its index in `text`."""
    out, idx = [], []
    i = 0
    while i < len(text):
        c = text[i]
        if c in _SKEL_DROP:
            i += 1
            continue
        if c == "र" and i + 1 < len(text) and text[i + 1] == "व":  # ख is often read as रव
            out.append("स")
            idx.append(i)
            i += 2
            continue
        c = _SKEL_MAP.get(c, c).lower()
        if c in ".:;,।|'’`\"()[]/\\-_":
            c = " "
        if c == " " and out and out[-1] == " ":
            i += 1
            continue
        out.append(c)
        idx.append(i)
        i += 1
    return "".join(out), idx
_SEPARATORS = " \t:;-–—.,।|_/\\()[]{}'\"`"


def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text).translate(ZERO_WIDTH).translate(DEV_TO_ASCII)
    return re.sub(r"\s+", " ", text).strip()


def strip_separators(text: str) -> str:
    return text.strip(_SEPARATORS + " ")


def label_key(text: str) -> str:
    """Loose form used only for fuzzy label matching."""
    text = clean(text).lower()
    text = text.replace("़", "")  # nukta
    text = re.sub(r"[:;.,।|_\-–—/\\()\[\]'\"`]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fix_digits(token: str) -> str:
    """Map letter look-alikes to digits, but only in tokens that are mostly digits, or
    made only of look-alike characters and number punctuation ("Il.ll" -> "11.11")."""
    core = re.sub(r"[^0-9A-Za-z|!$]", "", token)
    if not core:
        return token
    digits = sum(c.isdigit() for c in core)
    lookalike_only = re.fullmatch(r"[0-9OoIlL|!.,/$]+", token) is not None and len(core) >= 2
    if digits / len(core) < 0.5 and not lookalike_only:
        return token
    return token.translate(_DIGIT_LOOKALIKE)


def is_devanagari(text: str) -> bool:
    return any("ऀ" <= c <= "ॿ" for c in text)


def letters_only(text: str) -> str:
    """Keep letters (any script, incl. combining marks) and spaces."""
    out = []
    for c in text:
        cat = unicodedata.category(c)
        if cat[0] in ("L", "M") or c == " ":
            out.append(c)
        else:
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()
