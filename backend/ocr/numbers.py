"""Re-read number tokens with an English-only recogniser.

Khasra, survey, mutation and registration numbers are the fields a land record is looked up
by, and they are where the combined Hindi+English model is weakest: it decodes Latin digits
as Devanagari ones or as letters that look like them ("190/4" as "/q0/4", "1996/40440" as
"/११6/५०५५०"). An English-only recogniser has no Devanagari in its alphabet and reads the
same crops correctly. It is only ever asked about tokens the main model is unsure of, so
text it cannot represent - anything with a Devanagari letter in it - is left alone.
"""
from __future__ import annotations

import os

import numpy as np

NUMBER_PASS = os.getenv("LL_OCR_NUMBER_PASS", "1") != "0"
MAX_CONFIDENCE = float(os.getenv("LL_OCR_NUMBER_MAX_CONF", "0.5"))   # only tokens read unsurely
MIN_GAIN = float(os.getenv("LL_OCR_NUMBER_MIN_GAIN", "0.15"))        # and only a clear improvement

LATIN_DIGITS = set("0123456789")
DEV_DIGITS = {chr(0x966 + i) for i in range(10)}  # "०" is 0, "९" is 9
# characters the main model produces in place of digits, plus the separators real numbers use
LOOKALIKE = set("IilOoSsBZqg")   # "|" and quotes are strays, not stand-ins for a digit
SEPARATORS = set("/-. ,:")


def is_devanagari_letter(ch: str) -> bool:
    return "\u0900" <= ch <= "\u097f" and ch not in DEV_DIGITS


def looks_numeric(text: str) -> bool:
    """A token that is meant to be a number, however badly it came out.

    Two kinds are left alone. Anything with a Devanagari letter in it, because the English
    model cannot write it back. And anything written mostly in Devanagari digits: a date
    that came out as "०२/०३/२००२" is already right - extraction reads Devanagari digits -
    and asking a model that has no Devanagari to re-read it only invites "03/03/3002".
    What is worth a second look is a number that came out in Latin digits, or one with a
    letter in it that no number can contain (the "S" of "S४५", the "q" of "/q०/4")."""
    chars = [c for c in text if not c.isspace()]
    if not chars or any(is_devanagari_letter(c) for c in chars):
        return False
    latin = sum(1 for c in chars if c in LATIN_DIGITS)
    devanagari = sum(1 for c in chars if c in DEV_DIGITS)
    if latin + devanagari < 1:
        return False
    if latin == 0 and not any(c in LOOKALIKE for c in chars):
        return False  # a number written entirely in Devanagari digits, and nothing odd in it
    countable = sum(1 for c in chars if c in LATIN_DIGITS or c in DEV_DIGITS or c in LOOKALIKE or c in SEPARATORS)
    return countable / len(chars) >= 0.6


def is_number(text: str) -> bool:
    """Did the second reading actually come back as a number?"""
    chars = [c for c in text if not c.isspace()]
    return bool(chars) and sum(1 for c in chars if c in LATIN_DIGITS) / len(chars) >= 0.6


def refine_numbers(image: np.ndarray, tokens: list[dict], eng) -> int:
    """Replace unsure number tokens in place; returns how many were changed."""
    read = getattr(eng, "read_numbers", None)
    if read is None:
        return 0
    idx = [i for i, t in enumerate(tokens) if t["confidence"] < MAX_CONFIDENCE and looks_numeric(t["text"])]
    if not idx:
        return 0
    changed = 0
    for i, better in zip(idx, read(image, [tokens[i]["bbox"] for i in idx])):
        if not better or not better["text"] or better["text"] == tokens[i]["text"]:
            continue
        if better["confidence"] - tokens[i]["confidence"] < MIN_GAIN or not is_number(better["text"]):
            continue
        tokens[i] = {**tokens[i], "text": better["text"], "confidence": better["confidence"]}
        changed += 1
    return changed
