"""Rule-based duplicate detection against already stored records."""
from __future__ import annotations

from rapidfuzz import fuzz

from .normalize import label_key


def _same(a, b) -> bool:
    return a is not None and b is not None and str(a).strip().lower() == str(b).strip().lower()


# Digits the recogniser actually confuses on these documents, measured over the test split:
# 1805/1 came back as 1305/1, 1501/4 as 501/4, 1263/9क as 12639क, 273/6ग as 273/6".
CONFUSABLE = [set("38"), set("05o"), set("1il/"), set("69"), set("57"), set("2z")]


def _bare(value) -> str:
    """The identifier with the separators and stray marks OCR adds or drops taken out."""
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _one_char_apart(a: str, b: str) -> bool:
    """True when the two differ by a single character that the recogniser is known to confuse,
    or by one character being dropped. Only for identifiers long enough for that to be a
    misreading rather than a different parcel."""
    if abs(len(a) - len(b)) > 1 or min(len(a), len(b)) < 3:
        return False
    if len(a) == len(b):
        diff = [(x, y) for x, y in zip(a, b) if x != y]
        return len(diff) == 1 and any({diff[0][0], diff[0][1]} <= group for group in CONFUSABLE)
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    return any(longer[:i] + longer[i + 1:] == shorter for i in range(len(longer)))


def near_khasra(a, b) -> tuple[bool, str]:
    """Is this the same parcel number, read twice?

    Exact first. Then the same number once the separators OCR loses are taken out. Then one
    character out, where that character is one the recogniser is known to confuse. Anything
    looser than that would start joining parcels that are genuinely different."""
    if a is None or b is None:
        return False, ""
    if _same(a, b):
        return True, "same"
    ba, bb = _bare(a), _bare(b)
    if ba and ba == bb:
        return True, "same once separators are ignored"
    if ba and bb and _one_char_apart(ba, bb):
        return True, "one character apart"
    return False, ""


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
        matched, how = None, ""
        for p in rec_parcels:
            for q in ex_parcels:
                ok, why = near_khasra(p.get("khasra_number"), q.get("khasra_number"))
                if ok and (matched is None or why == "same"):
                    matched, how = p.get("khasra_number"), why
                    if why == "same":
                        break
            if how == "same":
                break
        if matched:
            # a near match is real evidence but not the same evidence: it scores lower, so a
            # near khasra on its own cannot reach the threshold without the khata or the owner
            score += 0.6 if how == "same" else 0.45
            reasons.append(f"same village + khasra ({matched})" if how == "same"
                           else f"same village + khasra {matched} ({how})")
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
