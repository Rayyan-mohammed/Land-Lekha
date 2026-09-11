"""Rule-based duplicate detection against already stored records."""
from __future__ import annotations

from rapidfuzz import fuzz

from .normalize import label_key


def _same(a, b) -> bool:
    return a is not None and b is not None and str(a).strip().lower() == str(b).strip().lower()


def find_duplicates(record: dict, existing: list[dict], min_score: float = 0.7) -> list[dict]:
    """`record` / `existing` are flat dicts of field values (plus `record_id` for existing).

    Scoring: a parcel is identified by (district, village, khasra); an account by
    (district, village, khata). Same parcel + similar owner is almost certainly the
    same record; same parcel with a different owner may be a sale not yet mutated.
    """
    out = []
    for ex in existing:
        reasons, score = [], 0.0
        same_loc = _same(record.get("district"), ex.get("district")) and _same(record.get("village"), ex.get("village"))
        if not same_loc:
            continue
        if _same(record.get("khasra_number"), ex.get("khasra_number")):
            score += 0.6
            reasons.append("same village + khasra")
        if _same(record.get("khata_number"), ex.get("khata_number")):
            score += 0.3
            reasons.append("same khata")
        if record.get("owner_name") and ex.get("owner_name"):
            sim = fuzz.token_sort_ratio(label_key(record["owner_name"]), label_key(ex["owner_name"])) / 100
            if sim >= 0.85:
                score += 0.2
                reasons.append(f"owner name {sim:.0%} similar")
        if score >= min_score:
            out.append({"record_id": ex["record_id"], "score": round(min(score, 1.0), 2), "reasons": reasons})
    return sorted(out, key=lambda d: -d["score"])
