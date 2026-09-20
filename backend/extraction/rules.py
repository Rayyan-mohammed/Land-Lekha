"""Cross-field checks, with an id and a plain explanation for each.

A rule that only says "consistency failed: tehsil_in_district" tells a verifier nothing they
can act on. Every rule here carries a stable id (so it can be counted on a dashboard and
quoted in a report), a plain sentence in English and in Hindi, and the two values that
disagree - which is what a person needs to decide which of the two is the misreading.

Rules are advisory. None of them rewrites a value; a failed rule sends the document to a
person with the reason attached.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    id: str
    en: str
    hi: str


RULES: dict[str, Rule] = {
    "LOC-1": Rule("LOC-1", "the district does not belong to that state",
                  "यह जिला उस राज्य में नहीं आता"),
    "LOC-2": Rule("LOC-2", "the tehsil does not belong to that district",
                  "यह तहसील उस जिले में नहीं आती"),
    "LOC-3": Rule("LOC-3", "the village does not belong to that tehsil",
                  "यह गाँव उस तहसील में नहीं आता"),
    "AREA-1": Rule("AREA-1", "the area is larger than any plot in this record set",
                   "क्षेत्रफल इस अभिलेख समूह के किसी भी भूखंड से बड़ा है"),
    "AREA-2": Rule("AREA-2", "the parcel areas do not add up to the total area",
                   "खसरों का क्षेत्रफल कुल क्षेत्रफल से मेल नहीं खाता"),
    "DATE-1": Rule("DATE-1", "the mutation is dated before the registration",
                   "नामांतरण की तारीख पंजीकरण से पहले की है"),
    "DATE-2": Rule("DATE-2", "the date is in the future",
                   "तारीख भविष्य की है"),
    "ID-1": Rule("ID-1", "the same khasra number appears on two different khatas",
                 "एक ही खसरा संख्या दो अलग खातों पर है"),
    "ROW-1": Rule("ROW-1", "a khasra row was read unsurely and needs checking",
                  "एक खसरा पंक्ति ठीक से नहीं पढ़ी गई, उसे जाँचें"),
}

# the old check names, so anything already stored keeps its meaning
LEGACY_IDS = {"district_in_state": "LOC-1", "tehsil_in_district": "LOC-2",
              "village_in_tehsil": "LOC-3"}


def explain(check: str, lang: str = "en") -> str:
    """The sentence for a rule id, or for one of the names used before ids existed."""
    rule = RULES.get(check) or RULES.get(LEGACY_IDS.get(check, ""))
    if rule is None:
        return check
    return rule.hi if lang == "hi" else rule.en


def failed(checks: list[dict]) -> list[dict]:
    return [c for c in checks if not c.get("ok", True)]


def check_dates(fields: dict) -> list[dict]:
    """Dates that cannot both be true. A mutation records a transfer that has already been
    registered, so it cannot predate it, and neither can have happened tomorrow."""
    from datetime import date

    out: list[dict] = []

    def parsed(name):
        f = fields.get(name) or {}
        iso = (f.get("normalized") or {}).get("iso") if isinstance(f.get("normalized"), dict) else None
        if not iso:
            return None
        try:
            return date.fromisoformat(iso)
        except ValueError:
            return None

    mutation, registration = parsed("mutation_date"), parsed("registration_date")
    if mutation and registration:
        out.append({"check": "DATE-1", "ok": mutation >= registration,
                    "detail": f"{mutation.isoformat()} / {registration.isoformat()}"})
    today = date.today()
    for name in ("mutation_date", "registration_date"):
        d = parsed(name)
        if d:
            out.append({"check": "DATE-2", "ok": d <= today, "detail": f"{name} {d.isoformat()}"})
    return out


def check_areas(fields: dict, parcels: list[dict] | None) -> list[dict]:
    """The khasra rows should account for the area on the document. A row lost to a bad read
    shows up here as a shortfall rather than passing unnoticed."""
    out: list[dict] = []
    total = ((fields.get("plot_area") or {}).get("normalized") or {}).get("hectares")
    rows = [((p.get("plot_area_normalized") or {}).get("hectares")) for p in (parcels or [])]
    rows = [r for r in rows if isinstance(r, (int, float))]
    if isinstance(total, (int, float)) and len(rows) > 1:
        summed = sum(rows)
        # a tenth of a hectare of slack: areas are printed to three decimals and rounded
        out.append({"check": "AREA-2", "ok": abs(summed - total) <= max(0.1, 0.05 * total),
                    "detail": f"{summed:.3f} ha in {len(rows)} rows / {total:.3f} ha on the record"})
    return out


def check_rows(parcels: list[dict] | None, threshold: float) -> list[dict]:
    """Khasra rows below the trust threshold.

    Only the first row used to reach the flat fields, so a wrong value in the second row had
    nothing to flag it. Each row now carries the confidence of its weakest cell; anything
    below the threshold is named here with the row number, so a verifier knows which line of
    the table to look at."""
    out = []
    for i, row in enumerate(parcels or []):
        conf = row.get("confidence")
        if conf is None or conf >= threshold:
            continue
        weakest = min((row.get("cell_confidence") or {"": conf}).items(), key=lambda kv: kv[1])
        out.append({"check": "ROW-1", "ok": False,
                    "detail": f"row {i + 1}: {weakest[0] or 'row'} at {conf:.2f}"})
    return out
