"""Track B entry point: OCR JSON -> structured, validated fields (docs/contracts.md)."""
from __future__ import annotations

from . import gazetteer
from .confidence import default_threshold, field_confidence, overall_confidence, route
from .learning import CorrectionMemory
from .parser import Candidate, build_lines, detect_document_type, generate_candidates, split_owners
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

    # 1b. co-owners: a Khatauni khata can list several ("Ram एवं Shyam"). The single
    # owner_name/father_name fields above always stay equal to the first entry.
    owners_list: list[dict] = []
    if "owner_name" in chosen:
        oc, _ = chosen["owner_name"]
        name_parts = split_owners(oc.text)
        father_parts = split_owners(chosen["father_name"][0].text) if "father_name" in chosen else []
        if len(name_parts) > 1:
            for i, nm in enumerate(name_parts):
                fp = PARSERS["father_name"](father_parts[i]) if i < len(father_parts) else None
                owners_list.append({"owner_name": PARSERS["owner_name"](nm).value,
                                    "father_name": fp.value if fp else None})
            fields["owner_name"] = _field("owner_name", oc, PARSERS["owner_name"](name_parts[0]))
            if "father_name" in chosen:
                fc, _ = chosen["father_name"]
                fp0 = PARSERS["father_name"](father_parts[0]) if father_parts else Parsed(None, 0.0)
                fields["father_name"] = _field("father_name", fc, fp0)
        else:
            owners_list.append({"owner_name": fields["owner_name"]["value"],
                                "father_name": fields.get("father_name", {}).get("value")})

    # 2. places against master database
    raw_places = {lvl: chosen[lvl][1].value for lvl in PLACE_LEVELS if lvl in chosen and chosen[lvl][1].value}
    matches, consistency = gazetteer.resolve(raw_places)
    for lvl, (place, score) in matches.items():
        c, p = chosen[lvl]
        if place is not None and score >= 0.7:
            fixed = Parsed(place.en, score, [] if score >= 0.9 else [f"matched master '{place.en}' at {score:.0%}"],
                           {"en": place.en, "hi": place.hi, "hi_verified": place.verified, "read_as": p.value})
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
            "source": "inferred", "normalized": {"en": parent_place.en, "hi": parent_place.hi,
                                                 "hi_verified": parent_place.verified},
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

    # 3b. parcel rows: a Khatauni khata can list several khasra/area/class rows. The
    # single khasra_number/plot_area/land_classification fields stay equal to row 0.
    def _below_rows(name: str) -> list[Candidate]:
        rows = [c for c in by_field.get(name, []) if c.source == "below"]
        rows.sort(key=lambda c: c.bbox[1] if c.bbox else 0)
        return rows

    khasra_rows = _below_rows("khasra_number")
    area_rows = _below_rows("plot_area")
    class_rows = _below_rows("land_classification")
    parcels_list: list[dict] = []
    if max(len(khasra_rows), len(area_rows), len(class_rows)) > 1:
        # Rows are matched by vertical position, not list index: if OCR drops a single
        # cell in one column (e.g. a blank land-classification box), naive index-zip
        # would shift every row after it and misalign the remaining columns.
        columns = {"khasra_number": khasra_rows, "plot_area": area_rows, "land_classification": class_rows}
        anchor_name = max(columns, key=lambda n: len(columns[n]))
        anchors = [c.bbox[1] for c in columns[anchor_name] if c.bbox]
        gaps = [b - a for a, b in zip(anchors, anchors[1:])]
        tolerance = max(15, (sorted(gaps)[len(gaps) // 2] if gaps else 30) * 0.5)
        used = {name: set() for name in columns}

        def _nearest(name: str, y: float):
            best_idx, best_dist = None, tolerance
            for idx, c in enumerate(columns[name]):
                if idx in used[name] or not c.bbox:
                    continue
                dist = abs(c.bbox[1] - y)
                if dist <= best_dist:
                    best_idx, best_dist = idx, dist
            if best_idx is not None:
                used[name].add(best_idx)
                return columns[name][best_idx]
            return None

        row_ys = anchors or [c.bbox[1] for c in (area_rows or class_rows) if c.bbox]
        for y in row_ys:
            row: dict = {}
            k = _nearest("khasra_number", y)
            if k:
                row["khasra_number"] = PARSERS["khasra_number"](k.text).value
            a = _nearest("plot_area", y)
            if a:
                ap = parse_area(a.text, find_unit(a.context), bigha, default_unit)
                row["plot_area"] = ap.value
                row["plot_area_normalized"] = ap.normalized
            cl = _nearest("land_classification", y)
            if cl:
                row["land_classification"] = PARSERS["land_classification"](cl.text).value
            parcels_list.append(row)
        if khasra_rows:
            fields["khasra_number"] = _field("khasra_number", khasra_rows[0], PARSERS["khasra_number"](khasra_rows[0].text))
        if area_rows:
            fields["plot_area"] = _field("plot_area", area_rows[0],
                                         parse_area(area_rows[0].text, find_unit(area_rows[0].context), bigha, default_unit))
        if class_rows:
            fields["land_classification"] = _field("land_classification", class_rows[0],
                                                    PARSERS["land_classification"](class_rows[0].text))
    elif any(n in fields for n in ("khasra_number", "plot_area", "land_classification")):
        parcels_list.append({
            "khasra_number": fields.get("khasra_number", {}).get("value"),
            "plot_area": fields.get("plot_area", {}).get("value"),
            "plot_area_normalized": fields.get("plot_area", {}).get("normalized"),
            "land_classification": fields.get("land_classification", {}).get("value"),
        })

    # 4. duplicates + routing
    flat = {k: v["value"] for k, v in fields.items()}
    flat["owners"], flat["parcels"] = owners_list, parcels_list
    dups = []
    if existing_records:
        from .duplicates import find_duplicates

        dups = find_duplicates(flat, existing_records)
    field_thresholds = memory.field_thresholds(threshold) if memory else None
    decision, reasons = route(fields, consistency, dups, threshold, field_thresholds)

    ordered = {n: fields[n] for n in FIELD_NAMES if n in fields}
    doc_type = detect_document_type(lines)
    return {
        "document_type": doc_type["type"],
        "document_type_family": doc_type["family"],
        "document_type_confidence": doc_type["confidence"],
        "document_type_also_seen": doc_type["also_seen"],
        "fields": ordered,
        "missing": [n for n in FIELD_NAMES if n not in fields],
        "missing_required": [n for n in REQUIRED_FIELDS if n not in fields],
        "overall_confidence": overall_confidence(ordered),
        "route": decision,
        "route_reasons": reasons,
        "consistency": consistency,
        "duplicates": dups,
        "threshold": threshold,
        "owners": owners_list,
        "parcels": parcels_list,
    }
