"""Label spotting and value-candidate generation on OCR lines.

Records put values in three places relative to their label, so we look in all three:
  * same_line  - "खाता संख्या : 00245"          (key : value forms)
  * near_right - value written a bit above/below the label's baseline (filled forms)
  * below      - value in the cell under a column header (Khatauni tables)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from .labels import ALIAS_INDEX
from .normalize import clean, label_key, skeleton, strip_separators


@dataclass
class Span:
    """A piece of a line: character range + geometry + OCR confidence."""
    text: str
    bbox: list[int]
    confidence: float
    line: int
    page: int


@dataclass
class LabelHit:
    field: str
    score: float  # 0..1
    line: int
    start: int  # char offsets in the line's key text
    end: int
    bbox: list[int]


@dataclass
class Candidate:
    field: str
    text: str
    bbox: list[int] | None
    ocr_confidence: float
    label_score: float
    source: str
    page: int
    context: str = ""  # extra text near the label (e.g. unit in a table header)


class Line:
    """An OCR line with a char -> token map, so any substring can be located."""

    def __init__(self, idx: int, page: int, line: dict, tokens: list[dict]):
        self.idx, self.page = idx, page
        self.bbox = line["bbox"]
        self.tokens = [tokens[i] for i in line["token_ids"]]
        parts, self.char_tok = [], []
        for ti, tok in enumerate(self.tokens):
            t = clean(tok["text"])
            if parts:
                parts.append(" ")
                self.char_tok.append(-1)
            parts.append(t)
            self.char_tok.extend([ti] * len(t))
        self.text = "".join(parts)
        self.height = max(1, self.bbox[3] - self.bbox[1])

    def span(self, a: int, b: int) -> Span | None:
        """Geometry + confidence for text[a:b] (x interpolated inside partial tokens)."""
        a, b = max(0, a), min(len(self.text), b)
        while a < b and self.text[a] == " ":
            a += 1
        while b > a and self.text[b - 1] == " ":
            b -= 1
        if a >= b:
            return None
        tis = sorted({self.char_tok[i] for i in range(a, b) if self.char_tok[i] >= 0})
        if not tis:
            return None
        xs0, xs1, confs, weights = [], [], [], []
        for ti in tis:
            tok = self.tokens[ti]
            chars = [i for i in range(len(self.text)) if self.char_tok[i] == ti]
            c0, c1 = chars[0], chars[-1] + 1
            lo, hi = max(a, c0), min(b, c1)
            x0, _, x1, _ = tok["bbox"]
            w = (x1 - x0) / max(1, c1 - c0)
            xs0.append(x0 + (lo - c0) * w)
            xs1.append(x0 + (hi - c0) * w)
            confs.append(tok["confidence"])
            weights.append(hi - lo)
        ys0 = [self.tokens[t]["bbox"][1] for t in tis]
        ys1 = [self.tokens[t]["bbox"][3] for t in tis]
        conf = sum(c * w for c, w in zip(confs, weights)) / max(1, sum(weights))
        return Span(self.text[a:b], [int(min(xs0)), min(ys0), int(max(xs1)), max(ys1)], round(conf, 4), self.idx, self.page)


_ALIAS_SKEL = [(f, s, len(s.split())) for f, a, _ in ALIAS_INDEX if (s := skeleton(clean(a))[0].strip())]
_LABEL_TAIL = re.compile(r"\s*([s5] name|name|no|number|नं|सं|का नाम)(?= |$)")


def _min_similarity(alias: str) -> float:
    n = len(alias)
    return 0.70 if n >= 7 else 0.75 if n >= 5 else 0.74


def find_labels(line: Line) -> list[LabelHit]:
    """All non-overlapping label matches in a line.

    Each alias is compared with windows of whole words (same word count +-1) on the
    Devanagari skeleton (see normalize.skeleton), so dropped matras / anusvara and
    single misread letters still match, but "Tehsil" never matches inside "TEHSILDAR".
    """
    sk, idx = skeleton(line.text)
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", sk)]
    hits: list[tuple[float, int, str, int, int]] = []
    for field, ask, kw in _ALIAS_SKEL:
        need = _min_similarity(ask)
        for k in {max(1, kw - 1), kw, kw + 1}:
            for i in range(len(words) - k + 1):
                a, b = words[i][0], words[i + k - 1][1]
                if abs((b - a) - len(ask)) > max(2, len(ask) // 3):
                    continue
                sim = Levenshtein.normalized_similarity(ask, sk[a:b])
                if sim < need:
                    continue
                # very short labels ("area", "ग्राम") only count at the start of a line or after
                # a separator, where labels actually sit
                if len(ask) <= 4 and sim < 1.0 and i > 0:
                    continue
                hits.append((sim * 100, len(ask), field, a, b))
    hits.sort(key=lambda h: (-h[0], -h[1]))
    chosen: list[tuple[float, int, str, int, int]] = []
    for h in hits:
        if all(h[4] <= c[3] or h[3] >= c[4] for c in chosen):
            chosen.append(h)
    chosen.sort(key=lambda h: h[3])
    # merge adjacent hits of the same field ("खाता संख्या / Khata No.")
    merged: list[list] = []
    for h in chosen:
        if merged and merged[-1][2] == h[2] and sk[merged[-1][4]:h[3]].strip() == "":
            merged[-1][4] = h[4]
            merged[-1][0] = max(merged[-1][0], h[0])
        else:
            merged.append(list(h))
    out = []
    for score, _, field, a, b in merged:
        # extend over trailing fragments of the label itself: "No.", "'s Name", "नं"
        m = _LABEL_TAIL.match(sk[b:])
        if m:
            b += m.end()
        oa, ob = idx[a], idx[b - 1] + 1
        sp = line.span(oa, ob)
        if sp:
            out.append(LabelHit(field, score / 100, line.idx, oa, ob, sp.bbox))
    return out


def same_line_value(line: Line, hit: LabelHit, hits: list[LabelHit]) -> tuple[Span | None, str]:
    nxt = min((h.start for h in hits if h.start >= hit.end and h is not hit), default=len(line.text))
    seg = line.text[hit.end:nxt]
    lead = len(seg) - len(seg.lstrip(" :;-–—.।|/"))
    sp = line.span(hit.end + lead, nxt)
    if sp is None or not strip_separators(sp.text):
        return None, seg
    return sp, seg


def _meaningful(text: str) -> bool:
    """False for empty values or bracketed annotations like "(हेक्टेयर)" in a table header."""
    t = text.strip(" :;-–—.।|/")
    if not t or t.startswith(("(", "[")):
        return False
    t = strip_separators(t)
    return sum(unicodedata.category(c)[0] in "LMN" for c in t) >= 2


def generate_candidates(lines: list[Line]) -> tuple[list[Candidate], dict[int, list[LabelHit]]]:
    hits_by_line = {ln.idx: find_labels(ln) for ln in lines}
    cands: list[Candidate] = []
    for ln in lines:
        hits = hits_by_line[ln.idx]
        for hit in hits:
            sp, remainder = same_line_value(ln, hit, hits)
            if sp:
                cands.append(Candidate(hit.field, sp.text, sp.bbox, sp.confidence, hit.score, "same_line", ln.page))
                # a value that looks like just a unit / bracket (table header "क्षेत्रफल (हेक्टेयर)") still
                # means the real value is elsewhere
                if _meaningful(sp.text):
                    continue
            lx0, ly0, lx1, ly1 = hit.bbox
            lh = max(1, ly1 - ly0)
            lcy = (ly0 + ly1) / 2
            next_label_x = min((h.bbox[0] for h in hits if h.bbox[0] > lx1), default=10**9)
            # near_right: tokens on other lines, to the right of the label, vertically close
            best = None
            for other in lines:
                if other.idx == ln.idx or other.page != ln.page:
                    continue
                if other.bbox[1] > ly1 + lh * 1.3 or other.bbox[3] < ly0 - lh * 1.3:
                    continue
                if hits_by_line[other.idx]:
                    continue  # that line has its own labels
                toks = [i for i, t in enumerate(other.tokens) if t["bbox"][0] >= lx1 - 5 and t["bbox"][0] < next_label_x]
                if not toks:
                    continue
                dist = abs((other.bbox[1] + other.bbox[3]) / 2 - lcy)
                if best is None or dist < best[0]:
                    best = (dist, other, toks)
            if best:
                _, other, toks = best
                a = min(i for i, t in enumerate(other.char_tok) if t == toks[0])
                b = max(i for i, t in enumerate(other.char_tok) if t == toks[-1]) + 1
                sp2 = other.span(a, b)
                if sp2:
                    cands.append(Candidate(hit.field, sp2.text, sp2.bbox, sp2.confidence, hit.score * 0.95,
                                           "near_right", ln.page, context=remainder))
            # below: table header -> every cell under it, until the table ends (a line with
            # its own label means a new section started, so the table stopped before it)
            col_w = lx1 - lx0
            below = sorted((o for o in lines if o.page == ln.page and o.idx != ln.idx
                            and ly1 - lh * 0.3 < o.bbox[1] <= ly1 + lh * 20), key=lambda o: o.bbox[1])
            for other in below:
                toks = [i for i, t in enumerate(other.tokens)
                        if lx0 - col_w * 0.6 <= (t["bbox"][0] + t["bbox"][2]) / 2 <= lx1 + col_w * 0.6]
                if not toks:
                    continue
                if hits_by_line[other.idx]:
                    break
                a = min(i for i, t in enumerate(other.char_tok) if t == toks[0])
                b = max(i for i, t in enumerate(other.char_tok) if t == toks[-1]) + 1
                sp3 = other.span(a, b)
                if sp3:
                    cands.append(Candidate(hit.field, sp3.text, sp3.bbox, sp3.confidence, hit.score * 0.9,
                                           "below", ln.page, context=remainder))
    return cands, hits_by_line


# "एव" is how OCR usually reads "एवं" (the anusvara dot is dropped); "एवम्" is the Sanskrit spelling
_OWNER_DELIMS = {"एवं", "एव", "एवँ", "एवम", "एवम्", "व", "and", "&"}
_OWNER_NUM_TOKEN = re.compile(r"^\d{1,2}[.)]$")


def split_owners(text: str) -> list[str]:
    """Real Khataunis list co-owners as "Ram एवं Shyam", "Ram, Shyam" or numbered
    lines ("1. Ram  2. Shyam"). Split on whole delimiter tokens only, so a name
    containing "व" mid-word (e.g. "श्रीवास्तव") is never cut."""
    groups: list[str] = []
    cur: list[str] = []
    toks = clean(text).replace(",", " , ").split()
    for i, tok in enumerate(toks):
        # "एवं" is also misread as "एच". As a name initial it is written "एच." and starts
        # a name, so only a bare "एच" between two names (2+ words before it) counts as "and"
        misread_and = tok == "एच" and len(cur) >= 2 and i + 1 < len(toks)
        if tok == "," or tok in _OWNER_DELIMS or misread_and or _OWNER_NUM_TOKEN.match(tok):
            if cur:
                groups.append(" ".join(cur))
                cur = []
        else:
            cur.append(tok)
    if cur:
        groups.append(" ".join(cur))
    return groups or [text.strip()]


def build_lines(ocr: dict) -> list[Line]:
    lines, idx = [], 0
    for page in ocr["pages"]:
        for ln in page["lines"]:
            lines.append(Line(idx, page["page"], ln, page["tokens"]))
            idx += 1
    return lines


def detect_document_type(lines: list[Line]) -> str:
    from .labels import DOC_TYPES

    head = " ".join(label_key(l.text) for l in lines[:8])
    for doc_type, words in DOC_TYPES:
        if any(fuzz.partial_ratio(label_key(w), head) >= 90 for w in words):
            return doc_type
    return "unknown"
