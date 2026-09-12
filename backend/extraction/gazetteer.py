"""Master location database: fuzzy lookup of state / district / tehsil / village
(Hindi or English spelling) and hierarchy consistency checks."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz

from .normalize import label_key, skeleton

MASTER = Path(__file__).parent / "master" / "gazetteer.json"


@dataclass(frozen=True)
class Place:
    level: str  # state | district | tehsil | village
    en: str
    hi: str
    state: str
    district: str | None = None
    tehsil: str | None = None
    # False for every village today: village Hindi spellings come from transliterate.py,
    # a rule-based guess, not a verified source (see that module's docstring). State/
    # district/tehsil Hindi names are the original hand-checked entries. If a genuinely
    # verified village is ever added, this level-based rule needs to become per-entry.
    verified: bool = True


@lru_cache(maxsize=1)
def load() -> dict:
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    places: dict[str, list[Place]] = {"state": [], "district": [], "tehsil": [], "village": []}
    states = {}
    for s in data["states"]:
        states[s["en"]] = s
        places["state"].append(Place("state", s["en"], s["hi"], s["en"]))
        for d in s["districts"]:
            places["district"].append(Place("district", d["en"], d["hi"], s["en"]))
            for t in d["tehsils"]:
                places["tehsil"].append(Place("tehsil", t["en"], t["hi"], s["en"], d["en"]))
                for v_en, v_hi in t["villages"]:
                    places["village"].append(Place("village", v_en, v_hi, s["en"], d["en"], t["en"], verified=False))
    return {"places": places, "states": states}


def state_info(state_en: str) -> dict | None:
    return load()["states"].get(state_en)


@lru_cache(maxsize=4096)
def _key(text: str) -> str:
    return skeleton(label_key(text))[0].strip()


def best_match(level: str, text: str, within: dict | None = None) -> tuple[Place | None, float]:
    """Best place at `level` for `text`; `within` restricts by parent (e.g. {"district": "Lucknow"})."""
    key = _key(text)
    if not key:
        return None, 0.0
    best, best_score = None, 0.0
    for p in load()["places"][level]:
        if within and any(getattr(p, k) != v for k, v in within.items() if v):
            continue
        score = max(fuzz.ratio(key, _key(p.en)), fuzz.ratio(key, _key(p.hi)))
        if score > best_score:
            best, best_score = p, score
    return best, best_score / 100


def resolve(raw: dict[str, str]) -> tuple[dict[str, tuple[Place | None, float]], list[dict]]:
    """Resolve raw place strings jointly. Returns matches per level and consistency checks."""
    out: dict[str, tuple[Place | None, float]] = {}
    checks: list[dict] = []
    for level in ("state", "district", "tehsil", "village"):
        if raw.get(level):
            out[level] = best_match(level, raw[level])

    def ok(level):
        p, s = out.get(level, (None, 0))
        return p if p is not None and s >= 0.7 else None

    # re-match children inside a confidently matched parent when the global best disagrees
    d, t = ok("district"), ok("tehsil")
    if d and raw.get("tehsil") and (not t or t.district != d.en):
        cand = best_match("tehsil", raw["tehsil"], {"district": d.en})
        if cand[1] >= out["tehsil"][1] - 0.1:
            out["tehsil"] = cand
    t = ok("tehsil")
    if t and raw.get("village"):
        cand = best_match("village", raw["village"], {"tehsil": t.en, "district": t.district})
        if cand[1] >= out["village"][1] - 0.1:
            out["village"] = cand

    s, d, t, v = ok("state"), ok("district"), ok("tehsil"), ok("village")
    if d and s:
        checks.append({"check": "district_in_state", "ok": d.state == s.en, "detail": f"{d.en} / {s.en}"})
    if t and d:
        checks.append({"check": "tehsil_in_district", "ok": t.district == d.en, "detail": f"{t.en} / {d.en}"})
    if v and t:
        checks.append({"check": "village_in_tehsil", "ok": v.tehsil == t.en, "detail": f"{v.en} / {t.en}"})
    return out, checks
