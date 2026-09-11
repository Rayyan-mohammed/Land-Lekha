"""Track B entry point: OCR JSON -> structured, validated fields (docs/contracts.md)."""
from __future__ import annotations

from . import gazetteer
from .confidence import default_threshold, field_confidence, overall_confidence, route
from .learning import CorrectionMemory
from .parser import Candidate, build_lines, detect_document_type, generate_candidates
from .schema import FIELD_NAMES, REQUIRED_FIELDS
from .validate import PARSERS, Parsed, find_unit, parse_area

SOURCE_WEIGHT = {"same_line": 1.0, "near_right": 0.97, "below": 0.93}
PLACE_LEVELS = ("state", "district", "tehsil", "village")


def _rank(c: Candidate, p: Parsed) -> float:
    validity = p.rule_score if p.valid else p.rule_score * 0.4
    return validity * SOURCE_WEIGHT.get(c.source, 0.9) * (0.6 + 0.4 * c.ocr_confidence) * (0.7 + 0.3 * c.label_score)


def _pick(field: str, cands: list[Candidate], parse, memory: CorrectionMemory | None):
    best = None
    for c in cands:
        learned = memory.lookup(field, c.text) if memory else None
        if learned:
            p = Parsed(learned, 1.0, ["learned correction applied"])
        else:
            p = parse(c)
        r = _rank(c, p) + (0.05 if learned else 0)
        if best is None or r > best[0]:
            best = (r, c, p, bool(learned))
    return best


def _place_parse(level: str, text: str) -> Parsed:
    """Place candidates are ranked by how well they match the master database. Leftover
    label words ("Tehsll इछावर") are dropped by trying every contiguous word span."""
    p = PARSERS[level](text)
    if p.value is None:
        return p
    words = p.value.split()
    best_text, best_score = p.value, gazetteer.best_match(level, p.value)[1]
    for i in range(len(words)):
        for j in range(i + 1, min(len(words), i + 4) + 1):
            if j - i == len(words):
                continue
            sub = " ".join(words[i:j])
            s = gazetteer.best_match(level, sub)[1] - 0.03  # prefer the full text on ties
            if s > best_score:
                best_text, best_score = sub, s
    return Parsed(best_text, max(0.3, best_score), p.issues)


def _field(name: str, c: Candidate, p: Parsed, source: str | None = None) -> dict:
    out = {
        "value": p.value,
        "raw": c.text,
        "confidence": 0.0,
        "ocr_confidence": round(c.ocr_confidence, 4),
        "label_score": round(c.label_score, 4),
        "rule_score": round(p.rule_score, 4),
        "valid": p.valid,
        "issues": list(p.issues),
        "page": c.page,
        "bbox": c.bbox,
        "source": source or c.source,
    }
    if p.normalized:
        out["normalized"] = p.normalized
    out["confidence"] = field_confidence(name, out)
    return out


def extract(ocr: dict, memory: CorrectionMemory | None = None, existing_records: list[dict] | None = None,
            threshold: float | None = None) -> dict:
    threshold = default_threshold() if threshold is None else threshold
    lines = build_lines(ocr)
    cands, _ = generate_candidates(lines)
    by_field: dict[str, list[Candidate]] = {}
    for c in cands:
        by_field.setdefault(c.field, []).append(c)

    fields: dict[str, dict] = {}
    chosen: dict[str, tuple[Candidate, Parsed]] = {}

    # 1. everything except area (area needs the state's bigha size)
    for name, cs in by_field.items():
        if name == "plot_area":
            continue
        parse = (lambda c, n=name: _place_parse(n, c.text)) if name in PLACE_LEVELS else \
            (lambda c, n=name: PARSERS[n](c.text))
        best = _pick(name, cs, parse, memory)
        if best:
            _, c, p, learned = best
            chosen[name] = (c, p)
            fields[name] = _field(name, c, p, source="learned" if learned else None)

    # 2. places against master database
    raw_places = {lvl: chosen[lvl][1].value for lvl in PLACE_LEVELS if lvl in chosen and chosen[lvl][1].value}
    matches, consistency = gazetteer.resolve(raw_places)
    for lvl, (place, score) in matches.items():
        c, p = chosen[lvl]
        if place is not None and score >= 0.7:
            fixed = Parsed(place.en, score, [] if score >= 0.9 else [f"matched master '{place.en}' at {score:.0%}"],
                           {"en": place.en, "hi": place.hi, "read_as": p.value})
        else:
            fixed = Parsed(p.value, min(score, 0.5), ["not found in master database"])
        fields[lvl] = _field(lvl, c, fixed)
    # infer missing (or unreadable) parents from a confidently matched child
    for child, parent in (("village", "tehsil"), ("tehsil", "district"), ("district", "state")):
        if child not in matches:
            continue
        if parent in fields and (fields[parent]["valid"] or parent == "tehsil"):
            continue  # village names repeat across tehsils, so never overwrite a read tehsil
        place, score = matches[child]
        if place is None or score < 0.85:
            continue
        pname = getattr(place, parent)
        if parent == "state":
            pname = place.state
        parent_place, _ = gazetteer.best_match(parent, pname)
        if parent_place is None:
            continue
        inferred = {
            "value": parent_place.en, "raw": None, "confidence": 0.0,
            "ocr_confidence": None, "label_score": None, "rule_score": 1.0, "valid": True,
            "issues": [f"inferred from {child} via master database"], "page": fields[child]["page"], "bbox": None,
            "source": "inferred", "normalized": {"en": parent_place.en, "hi": parent_place.hi},
        }
        inferred["confidence"] = min(field_confidence(parent, inferred), fields[child]["confidence"])
        fields[parent] = inferred
        matches[parent] = (parent_place, 1.0)

    # 3. area, using the state's bigha if known
    state_en = fields.get("state", {}).get("value")
    info = gazetteer.state_info(state_en) if state_en else None
    bigha = info["bigha_ha"] if info else 0.2529
    default_unit = info.get("area_unit") if info else None
    if "plot_area" in by_field:
        best = _pick("plot_area", by_field["plot_area"],
                     lambda c: parse_area(c.text, find_unit(c.context), bigha, default_unit), memory)
        if best:
            _, c, p, learned = best
            fields["plot_area"] = _field("plot_area", c, p, source="learned" if learned else None)

    # 4. duplicates + routing
    flat = {k: v["value"] for k, v in fields.items()}
    dups = []
    if existing_records:
        from .duplicates import find_duplicates

        dups = find_duplicates(flat, existing_records)
    field_thresholds = memory.field_thresholds(threshold) if memory else None
    decision, reasons = route(fields, consistency, dups, threshold, field_thresholds)

    ordered = {n: fields[n] for n in FIELD_NAMES if n in fields}
    return {
        "document_type": detect_document_type(lines),
        "fields": ordered,
        "missing": [n for n in FIELD_NAMES if n not in fields],
        "missing_required": [n for n in REQUIRED_FIELDS if n not in fields],
        "overall_confidence": overall_confidence(ordered),
        "route": decision,
        "route_reasons": reasons,
        "consistency": consistency,
        "duplicates": dups,
        "threshold": threshold,
    }
