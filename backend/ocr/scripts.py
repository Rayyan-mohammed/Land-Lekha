"""Which writing systems are on a page.

Moved out of the land/non-land classifier, which has been removed: this part earns its place
on its own. Knowing a page is Telugu rather than Devanagari is what lets the pipeline pick a
reader, and it is honest metadata for the repository - script, not language, because Hindi and
Marathi share Devanagari and nothing here can tell them apart.

The page's own text is never translated or rewritten. This only reports what was seen.
"""
from __future__ import annotations

# Unicode blocks, in the order we test them. Latin is handled separately because it is the
# one that shares a page with everything else.
BLOCKS: list[tuple[str, int, int]] = [
    ("Devanagari", 0x0900, 0x097F),
    ("Bengali", 0x0980, 0x09FF),
    ("Gurmukhi", 0x0A00, 0x0A7F),
    ("Gujarati", 0x0A80, 0x0AFF),
    ("Odia", 0x0B00, 0x0B7F),
    ("Tamil", 0x0B80, 0x0BFF),
    ("Telugu", 0x0C00, 0x0C7F),
    ("Kannada", 0x0C80, 0x0CFF),
    ("Malayalam", 0x0D00, 0x0D7F),
    ("Arabic", 0x0600, 0x06FF),
]

# EasyOCR language code for each script we can actually read today. A script with no reader
# here is still reported - saying "there is Tamil on this page and we cannot read it" is
# worth more than silence.
READERS: dict[str, str] = {
    "Devanagari": "hi",
    "Telugu": "te",
    "Tamil": "ta",
    "Kannada": "kn",
    "Bengali": "bn",
    "Latin": "en",
}

MIN_SHARE = 0.04   # below this a script is a stray character, not a language on the page


def script_of(ch: str) -> str | None:
    """The writing system one character belongs to, or None if it is not a letter."""
    if not ch.isalpha():
        return None
    code = ord(ch)
    if code < 0x0250:
        return "Latin"
    for name, lo, hi in BLOCKS:
        if lo <= code <= hi:
            return name
    return None


def script_shares(text: str) -> dict[str, float]:
    """Share of the page's letters written in each script, largest first."""
    counts: dict[str, int] = {}
    letters = 0
    for ch in text:
        name = script_of(ch)
        if name is None:
            continue
        letters += 1
        counts[name] = counts.get(name, 0) + 1
    if not letters:
        return {}
    shares = {name: n / letters for name, n in counts.items()}
    return dict(sorted(shares.items(), key=lambda kv: -kv[1]))


def detect_scripts(text: str, min_share: float = MIN_SHARE) -> list[str]:
    """Scripts that hold a real share of the page, largest first."""
    return [name for name, share in script_shares(text).items() if share >= min_share]


def readers_for(scripts: list[str]) -> list[str]:
    """EasyOCR language codes for those scripts, and which we cannot read.

    Returns (codes, unsupported). Latin is always included: every Indian land record we have
    seen carries some Latin, if only in the numbers."""
    codes, missing = [], []
    for name in scripts:
        code = READERS.get(name)
        if code is None:
            missing.append(name)
        elif code not in codes:
            codes.append(code)
    if "en" not in codes:
        codes.append("en")
    return codes, missing
