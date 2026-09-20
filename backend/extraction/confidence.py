"""Per-field confidence and the auto-accept / review routing rule.

Confidence is a calibrated probability that the extracted value is correct. A
logistic model (trained offline by eval/calibrate.py on the dev split, stored in
master/calibration.json) combines:
  * OCR confidence of the value's characters
  * rule score   - how well the value fits its format / the master database
  * label score  - how clearly the field's label was found
  * where the value came from (same line, below a header, inferred, learned)
  * field type and the number of validation issues
Raw OCR confidence alone is badly calibrated (correct Devanagari text often scores
0.4-0.6), which is why it is not used directly.

Without a calibration file a transparent weighted formula is used instead.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from .schema import FIELD_MAP, REQUIRED_FIELDS

CALIBRATION = Path(__file__).parent / "master" / "calibration.json"
DEFAULT_THRESHOLD = 0.80
W_OCR, W_RULE, W_LABEL = 0.5, 0.3, 0.2
INVALID_CAP = 0.45

SOURCES = ["same_line", "near_right", "below", "inferred", "learned"]
KINDS = ["name", "id", "area", "place", "date", "category"]
FEATURES = (["ocr", "rule", "label", "valid", "n_issues", "value_len"] + [f"src_{s}" for s in SOURCES]
            + [f"kind_{k}" for k in KINDS] + ["ocr_x_name", "ocr_x_id"])


def features(name: str, f: dict) -> list[float]:
    kind = FIELD_MAP[name].kind if name in FIELD_MAP else "id"
    ocr = f.get("ocr_confidence")
    ocr = 1.0 if ocr is None else float(ocr)
    label = f.get("label_score")
    x = {
        "ocr": ocr,
        "rule": float(f.get("rule_score") or 0.0),
        "label": 1.0 if label is None else float(label),
        "valid": float(bool(f.get("valid"))),
        "n_issues": float(len(f.get("issues") or [])),
        "value_len": min(len(str(f.get("raw") or f.get("value") or "")), 40) / 20,
        **{f"src_{s}": float(f.get("source") == s) for s in SOURCES},
        **{f"kind_{k}": float(kind == k) for k in KINDS},
        "ocr_x_name": ocr * (kind == "name"),
        "ocr_x_id": ocr * (kind == "id"),
    }
    return [x[k] for k in FEATURES]


@lru_cache(maxsize=1)
def calibration() -> dict | None:
    if not CALIBRATION.exists():
        return None
    cal = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    return cal if cal.get("features") == FEATURES else None  # stale file -> ignore


def default_threshold() -> float:
    cal = calibration()
    return float(cal["threshold"]) if cal else DEFAULT_THRESHOLD


def field_confidence(name: str, f: dict) -> float:
    cal = calibration()
    if cal:
        z = cal["intercept"] + sum(w * v for w, v in zip(cal["coef"], features(name, f)))
        c = 1 / (1 + math.exp(-z))
    else:
        ocr = 1.0 if f.get("ocr_confidence") is None else f["ocr_confidence"]
        label = 1.0 if f.get("label_score") is None else f["label_score"]
        c = W_OCR * ocr + W_RULE * (f.get("rule_score") or 0) + W_LABEL * label
    if not f.get("valid"):
        c = min(c, INVALID_CAP)
    return round(c, 4)


def route(fields: dict[str, dict], consistency: list[dict], duplicates: list[dict] | None = None,
          threshold: float | None = None,
          field_thresholds: dict[str, float] | None = None) -> tuple[str, list[str]]:
    threshold = default_threshold() if threshold is None else threshold
    reasons = []
    missing = [name for name in REQUIRED_FIELDS if name not in fields]
    if len(missing) == len(REQUIRED_FIELDS):
        # Nothing a land record must have was found anywhere on the page. This is what used to
        # be answered by a land/non-land gate before extraction; the routing rules already knew
        # it, they just said it seven times. Said once, the queue can sort these to the bottom.
        reasons.append(f"no land-record fields found ({len(missing)} of {len(REQUIRED_FIELDS)} "
                       "required fields missing)")
    else:
        for name in missing:
            reasons.append(f"missing required field: {name}")
    for name, f in fields.items():
        t = (field_thresholds or {}).get(name, threshold)
        if not f["valid"]:
            reasons.append(f"invalid {name}: {', '.join(f['issues']) or 'format'}")
        elif f["confidence"] < t:
            reasons.append(f"low confidence: {name} ({f['confidence']:.2f})")
    for c in consistency:
        if not c["ok"]:
            reasons.append(f"consistency failed: {c['check']} ({c['detail']})")
    for d in duplicates or []:
        reasons.append(f"possible duplicate of record {d['record_id']} ({', '.join(d['reasons'])})")
    return ("review" if reasons else "auto_accept"), reasons


def overall_confidence(fields: dict[str, dict]) -> float:
    if not fields:
        return 0.0
    total = weight = 0.0
    for name, f in fields.items():
        w = 2.0 if name in REQUIRED_FIELDS else 1.0
        total += f["confidence"] * w
        weight += w
    missing = [n for n in REQUIRED_FIELDS if n not in fields]
    weight += 2.0 * len(missing)
    return round(total / weight, 4)
