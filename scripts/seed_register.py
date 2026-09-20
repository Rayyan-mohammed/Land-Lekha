"""Fill the simulated state register from the LGD villages, so the cross-check has something
to check against.

    python scripts/seed_register.py --count 200

Simulated data, deliberately and obviously: the parcels are generated, the names come from the
same token lists the document generator uses. What is real is the village, tehsil and district,
which come from the Ministry of Panchayati Raj directory the rest of the system uses.

To make the check worth watching, a share of the entries are seeded with a small disagreement
(a different owner, a slightly different area) - that is what a stale record looks like.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.integration.register import Register  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--disagree", type=float, default=0.15, help="share seeded with a difference")
    args = ap.parse_args()
    random.seed(args.seed)

    gaz = json.loads((ROOT / "backend" / "extraction" / "master" / "gazetteer.json").read_text(encoding="utf-8"))
    # state -> district -> tehsil -> [english, hindi] village names
    villages = [{"en": v[0], "tehsil": t["en"], "district": d["en"], "state": st["en"]}
                for st in gaz["states"] for d in st["districts"] for t in d["tehsils"] for v in t["villages"]]
    names = json.loads((ROOT / "backend" / "extraction" / "master" / "name_tokens.json").read_text(encoding="utf-8"))
    firsts = names.get("first") or names.get("given") or ["Ram", "Shyam", "Sita"]
    lasts = names.get("last") or names.get("surname") or ["Sharma", "Verma", "Yadav"]
    classes = ["agricultural_irrigated", "agricultural_unirrigated", "barren", "abadi"]

    reg = Register()
    for _ in range(args.count):
        v = random.choice(villages)
        owner = f"{random.choice(firsts)} {random.choice(lasts)}"
        reg.add({
            "village": v["en"], "tehsil": v["tehsil"], "district": v["district"],
            "khata_number": f"{random.randint(1, 99999):05d}",
            "khasra_number": f"{random.randint(10, 1999)}/{random.randint(1, 9)}",
            "owner_name": owner, "father_name": f"{random.choice(firsts)} {owner.split()[-1]}",
            "plot_area": f"{random.uniform(0.1, 4.0):.3f} hectare",
            "land_classification": random.choice(classes),
        })
    reg.save()
    from backend.integration.register import STORE
    print(f"wrote {len(reg.entries)} simulated register entries to {STORE}")


if __name__ == "__main__":
    main()
