"""Rule-based duplicate detection against already stored records."""
from __future__ import annotations

from rapidfuzz import fuzz

from .normalize import label_key


def _same(a, b) -> bool:
    return a is not None and b is not None and str(a).strip().lower() == str(b).strip().lower()


def find_duplicates(record: dict, existing: list[dict], min_score: float = 0.7) -> list[dict]:
    """`record` / `existing` are flat dicts of field values (plus `record_id` for existing),
    plus optional `owners` / `parcels` lists for a khata with several co-owners or rows
    (see docs/contracts.md) - checked against every entry, not just the first.

    Scoring: a parcel is identified by (district, village, khasra); an account by
    (district, village, khata). Same parcel + similar owner is almost certainly the
    same record; same parcel with a different owner may be a sale not yet mutated.
    """
    out = []
    rec_parcels = record.get("parcels") or [{"khasra_number": record.get("khasra_number")}]
    rec_owners = record.get("owners") or [{"owner_name": record.get("owner_name")}]
    for ex in existing:
        reasons, score = [], 0.0
        same_loc = _same(record.get("district"), ex.get("district")) and _same(record.get("village"), ex.get("village"))
        if not same_loc:
            continue
        ex_parcels = ex.get("parcels") or [{"khasra_number": ex.get("khasra_number")}]
        matched = next((p.get("khasra_number") for p in rec_parcels for q in ex_parcels
                        if _same(p.get("khasra_number"), q.get("khasra_number"))), None)
        if matched:
            score += 0.6
            reasons.append(f"same village + khasra ({matched})")
        if _same(record.get("khata_number"), ex.get("khata_number")):
            score += 0.3
            reasons.append("same khata")
        ex_owners = ex.get("owners") or [{"owner_name": ex.get("owner_name")}]
        best_sim = max((fuzz.token_sort_ratio(label_key(o["owner_name"]), label_key(p["owner_name"])) / 100
                        for o in rec_owners for p in ex_owners if o.get("owner_name") and p.get("owner_name")),
                       default=0.0)
        if best_sim >= 0.85:
            score += 0.2
            reasons.append(f"owner name {best_sim:.0%} similar")
        if score >= min_score:
            out.append({"record_id": ex["record_id"], "score": round(min(score, 1.0), 2), "reasons": reasons})
    return sorted(out, key=lambda d: -d["score"])
