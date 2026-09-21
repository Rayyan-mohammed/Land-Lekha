"""Field-level validators. Each takes raw text and returns a Parsed result with a
normalised value, a rule score (0..1: how well the text fits the expected format)
and a list of issues. Business rules live here."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from . import names
from .labels import AREA_UNIT_WORDS, LAND_CLASS_WORDS
from .normalize import clean, fix_digits, is_devanagari, label_key, letters_only, skeleton, strip_separators


@dataclass
class Parsed:
    value: str | None
    rule_score: float
    issues: list[str] = field(default_factory=list)
    normalized: dict | None = None

    @property
    def valid(self) -> bool:
        return self.value is not None and self.rule_score >= 0.6


def _digits_fixed(text: str) -> str:
    return " ".join(fix_digits(t) for t in clean(text).split())


def parse_plain_number(text: str, max_len: int = 6) -> Parsed:
    t = strip_separators(_digits_fixed(text)).replace(" ", "")
    if re.fullmatch(rf"\d{{1,{max_len}}}", t):
        return Parsed(t, 1.0)
    m = re.search(rf"\d{{1,{max_len}}}", t)
    if m:
        return Parsed(m.group(), 0.65, ["extra characters around number"])
    return Parsed(None, 0.0, ["no number found"])


KHASRA_RE = re.compile(r"(\d{1,5})(?:/(\d{1,3}))?([A-Za-zकखगघ])?")


def parse_plot_id(text: str) -> Parsed:
    """Khasra / survey numbers: 123, 123/2, 123/2A, 123/2क."""
    t = clean(text)
    # a slash is often read as | or \ between digits
    t = re.sub(r"(?<=\d)\s*[|\\]\s*(?=\S)", "/", t)
    # keep a trailing Devanagari/latin letter suffix before digit-fixing mangles it
    t = re.sub(r"\s*/\s*", "/", t)
    parts = t.split()
    t = "".join(fix_digits(p) if not re.fullmatch(r"\d+/?\d*[A-Za-zकखगघ]", p) else p for p in parts)
    t = strip_separators(t)
    # the suffix letter ख is often read as स (never a valid suffix) or रव
    t = re.sub(r"(?<=\d)(स|रव)$", "ख", t)
    m = KHASRA_RE.fullmatch(t)
    if m:
        return Parsed(t, 1.0)
    m = KHASRA_RE.search(t)
    if m:
        # "39/^": the sub-number after the slash is unreadable - don't silently drop it
        if m.group(2) is None and t[m.end():m.end() + 1] == "/":
            return Parsed(m.group(), 0.45, ["unreadable part after '/'"])
        return Parsed(m.group(), 0.65, ["extra characters around plot number"])
    return Parsed(None, 0.0, ["no plot number found"])


def parse_registration(text: str) -> Parsed:
    t = re.sub(r"(?<=\d{4})\s*[|\\]\s*(?=\d)", "/", clean(text))  # year|number -> year/number
    t = strip_separators(_digits_fixed(t)).replace(" ", "")
    m = re.fullmatch(r"(\d{4})/(\d{1,6})", t)
    if m:
        year = int(m.group(1))
        if 1900 <= year <= date.today().year:
            return Parsed(t, 1.0)
        return Parsed(t, 0.6, ["registration year out of range"])
    m = re.search(r"\d{4}/\d{1,6}", t)
    if m:
        return Parsed(m.group(), 0.65, ["extra characters around registration number"])
    return parse_plain_number(text, 10)


DATE_RE = re.compile(r"(\d{1,2})\s*[/\-.|\\]\s*(\d{1,2})\s*[/\-.|\\]\s*(\d{2,4})")


def parse_date(text: str) -> Parsed:
    # "|" between digits is a misread "/" here, not a 1
    t = _digits_fixed(re.sub(r"(?<=\d)\|(?=\d)", "/", clean(text)))
    m = DATE_RE.search(t)
    if not m:
        return Parsed(None, 0.0, ["no date found"])
    d, mth, y = (int(g) for g in m.groups())
    if y < 100:
        y += 2000 if y <= date.today().year % 100 else 1900
    try:
        dt = datetime(y, mth, d).date()
    except ValueError:
        return Parsed(f"{d:02d}/{mth:02d}/{y}", 0.3, ["impossible date"])
    if not 1900 <= dt.year <= date.today().year or dt > date.today():
        return Parsed(dt.strftime("%d/%m/%Y"), 0.4, ["date out of range"])
    score = 1.0 if m.group(0) == strip_separators(t) else 0.8
    return Parsed(dt.strftime("%d/%m/%Y"), score)


def find_unit(text: str) -> str | None:
    key = label_key(text)
    for unit, words in AREA_UNIT_WORDS.items():
        for w in words:
            wk = label_key(w)
            if len(wk) <= 3:
                if re.search(rf"(^|\s|\d){re.escape(wk)}($|\s)", key):
                    return unit
            elif wk in key or fuzz.partial_ratio(wk, key) >= 88:
                return unit
    # one misread letter in a Devanagari unit word ("एझड" for "एकड़")
    tokens = skeleton(key)[0].split()
    for unit, words in AREA_UNIT_WORDS.items():
        for w in words:
            ws = skeleton(label_key(w))[0].strip()
            if is_devanagari(ws) and len(ws) >= 3 and any(
                    len(tok) == len(ws) and Levenshtein.distance(tok, ws) <= 1 for tok in tokens):
                return unit
    return None


# Hectares in one of each unit. Every unit find_unit() can return must be here: when gunta and
# cent were added to the vocabulary for Telugu records without a row in this table, any page
# mentioning them raised KeyError and the whole extraction died.
HECTARES_PER: dict[str, float] = {
    "hectare": 1.0,
    "acre": 0.404686,
    "sqm": 0.0001,
    "cent": 0.00404686,     # 1/100 acre - Andhra Pradesh, Telangana, Kerala, West Bengal
    "gunta": 0.0101171,     # 1/40 acre - Telangana, Karnataka, Maharashtra
    "kanal": 0.0505857,     # Haryana, Punjab, Himachal: 8 kanal to the acre
    "marla": 0.00252929,    # 20 marla to the kanal
}


def _kanal_marla(text: str) -> float | None:
    """"8 कनाल 16 मरला" / "8 kanal 16 marla" is one area written in two units, the way every
    Haryana and Punjab record writes it. Return it in kanal, or None if it is not that shape."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:कनाल|kanal)\S*\s*(\d+(?:\.\d+)?)\s*(?:मरला|marla)", text, re.I)
    return float(m.group(1)) + float(m.group(2)) / 20 if m else None


def parse_area(text: str, unit_hint: str | None = None, bigha_ha: float = 0.2529,
               default_unit: str | None = None) -> Parsed:
    """`unit_hint` comes from the label (table header "क्षेत्रफल (हेक्टेयर)"); `default_unit`
    is the state's customary unit, used (and flagged) only when no unit is readable."""
    t = clean(text)
    km = _kanal_marla(_digits_fixed(t))
    if km is not None:
        return Parsed(f"{km:g} kanal", 1.0, [],
                      {"value": km, "unit": "kanal", "hectares": round(km * HECTARES_PER["kanal"], 4)})
    num_part = re.sub(r"[:;'\"`]", " ", _digits_fixed(t).replace(",", "."))
    num_part = re.sub(r"\s+", " ", num_part)
    issues, score = [], 1.0
    m = re.search(r"\d+\s*\.\s*\d+", num_part)
    if m:
        value = float(m.group().replace(" ", ""))
    else:
        # decimal point lost in OCR: "3 48 acre" -> 3.48 (flagged, lower score)
        m = re.search(r"(\d{1,3}) (\d{1,4})(?!\d)", num_part)
        if m:
            value = float(f"{m.group(1)}.{m.group(2)}")
            issues.append("decimal point inferred")
            score = 0.75
        else:
            m = re.search(r"\d+", num_part)
            if not m:
                return Parsed(None, 0.0, ["no area value found"])
            digits = m.group()
            if len(digits) >= 2 and digits.startswith("0"):
                # "089" can only be "0.89": the dot was lost
                value = float(f"0.{digits[1:]}")
                issues.append("decimal point inferred")
                score = 0.75
            else:
                value = float(digits)
                if value >= 10:
                    # plot areas are almost always fractional; a large whole number usually
                    # means the dot was lost ("183" for 18.3). Flag it rather than guess.
                    issues.append("no decimal point - check value")
                    score = 0.7
    unit = find_unit(num_part[m.end():]) or find_unit(t) or unit_hint
    if unit is None and default_unit:
        unit, score = default_unit, min(score, 0.75)
        issues.append(f"unit not readable, assumed {default_unit} (state practice)")
    if unit is None:
        unit, score = "hectare", min(score, 0.6)
        issues.append("unit missing, assumed hectare")
    factor = HECTARES_PER.get(unit, bigha_ha if unit == "bigha" else None)
    if factor is None:
        # a unit the vocabulary knows but this table does not: say so rather than crash
        return Parsed(f"{value:g} {unit}", 0.4, issues + [f"no conversion for unit '{unit}'"],
                      {"value": value, "unit": unit, "hectares": None})
    ha = value * factor
    # "4167 hectare" is implausible for one plot but "4.167" is the usual 3-decimal format:
    # the decimal point was lost. Put it back, flagged.
    if unit == "hectare" and ha >= 200 and value.is_integer() and "decimal point inferred" not in issues:
        digits = str(int(value))
        if 4 <= len(digits) <= 5:
            value = float(f"{digits[:-3]}.{digits[-3:]}")
            ha = value
            issues.append("decimal point inferred")
            score = min(score, 0.7)
    # the same for acre and bigha, which records give to 2 decimals: "1293 bigha" (327 ha) is not
    # one plot, "12.93" is. A plausible whole number ("285 bigha", 72 ha) stays as read, flagged.
    if unit in ("acre", "bigha") and ha >= 200 and value.is_integer() and "decimal point inferred" not in issues:
        digits = str(int(value))
        if 3 <= len(digits) <= 5:
            value = float(f"{digits[:-2]}.{digits[-2:]}")
            ha = value * factor
            issues = [i for i in issues if i != "no decimal point - check value"] + ["decimal point inferred"]
            score = min(score, 0.7)
    if re.search(r"-\s*\d", num_part):
        # the digit regexes above only ever match unsigned digits, so a leading "-" would
        # otherwise be silently dropped and the value trusted as a normal positive reading
        issues.append("negative value read - area cannot be negative, sign dropped")
        score = min(score, 0.5)
    if not 0 < ha < 200:
        score = min(score, 0.4)
        issues.append("implausible plot area")
    return Parsed(f"{value:g} {unit}", score, issues, {"value": value, "unit": unit, "hectares": round(ha, 4)})


_LABEL_RESIDUE = {"s", "name", "नाम", "का", "no"}


def parse_name(text: str) -> Parsed:
    t = letters_only(clean(text))
    words = t.split()
    # drop leftovers of the label itself ("'s Name", "SNamne", "का नाम")
    while words and (words[0].lower() in _LABEL_RESIDUE or
                     (len(words) > 2 and fuzz.ratio(words[0].lower().lstrip("s$5"), "name") >= 75)):
        words = words[1:]
    if not words:
        return Parsed(None, 0.0, ["no name found"])
    issues, score = [], 1.0
    words, restored = names.restore(words)
    if restored:
        issues.append("spelling normalised from name lexicon")
    if len(words) > 5:
        words = words[:5]
        score, issues = 0.6, ["name too long, truncated"]
    name = " ".join(words)
    if len(name.replace(" ", "")) < 3:
        return Parsed(name, 0.3, ["name too short"])
    mixed = is_devanagari(name) and re.search(r"[A-Za-z]", name)
    if mixed:
        score = min(score, 0.7)
        issues.append("mixed scripts in name")
    if not is_devanagari(name):
        name = name.title()
    if re.search(r"\d", clean(text)):
        score = min(score, 0.75)
        issues.append("digits removed from name")
    return Parsed(name, score, issues)


def parse_land_class(text: str) -> Parsed:
    key = skeleton(label_key(text))[0].strip()
    if not key:
        return Parsed(None, 0.0, ["no land class found"])
    best, best_score = None, 0
    for cls, words in LAND_CLASS_WORDS.items():
        for w in words:
            s = fuzz.ratio(key, skeleton(label_key(w))[0].strip())
            if s > best_score:
                best, best_score = cls, s
    if best_score >= 60:
        return Parsed(best, best_score / 100)
    return Parsed(None, 0.0, [f"unknown land class '{text}'"])


def parse_place_text(text: str) -> Parsed:
    t = letters_only(clean(text))
    if not t:
        return Parsed(None, 0.0, ["no place name found"])
    return Parsed(t, 1.0)


PARSERS = {
    "owner_name": parse_name,
    "father_name": parse_name,
    "khata_number": lambda t: parse_plain_number(t, 6),
    "khasra_number": parse_plot_id,
    "survey_number": parse_plot_id,
    "mutation_number": lambda t: parse_plain_number(t, 6),
    "mutation_date": parse_date,
    "registration_number": parse_registration,
    "registration_date": parse_date,
    "land_classification": parse_land_class,
    "village": parse_place_text,
    "tehsil": parse_place_text,
    "district": parse_place_text,
    "state": parse_place_text,
}
