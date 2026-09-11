"""Rebuilds the village lists in master/gazetteer.json from real Ministry of
Panchayati Raj LGD data (master/lgd_villages.csv - see that file's header for
provenance), replacing the earlier hand-picked placeholder sample.

State/district/tehsil names, codes and metadata (bigha_ha, record_title, ...) are
untouched; only each matching tehsil's "villages" list is replaced. Hindi spellings
are filled in with backend/extraction/transliterate.py, which is a best-effort
approximation, NOT an official source - see that module's docstring.

    python -m backend.extraction.build_gazetteer
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .transliterate import to_devanagari

MASTER = Path(__file__).parent / "master"
GAZETTEER = MASTER / "gazetteer.json"
VILLAGES_CSV = MASTER / "lgd_villages.csv"


def load_villages() -> dict[tuple[str, str, str], list[tuple[str, str]]]:
    """(state, district, tehsil) -> [(english, hindi), ...], deduped by LGD code."""
    by_tehsil: dict[tuple[str, str, str], dict[str, str]] = defaultdict(dict)
    with VILLAGES_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["state"], row["district"], row["tehsil"])
            by_tehsil[key][row["lgd_village_code"]] = row["village_en"]
    return {key: sorted((en, to_devanagari(en)) for en in names.values())
            for key, names in by_tehsil.items()}


def main() -> None:
    villages = load_villages()
    gaz = json.loads(GAZETTEER.read_text(encoding="utf-8"))
    replaced = 0
    for state in gaz["states"]:
        for district in state["districts"]:
            for tehsil in district["tehsils"]:
                key = (state["en"], district["en"], tehsil["en"])
                if key in villages:
                    tehsil["villages"] = [list(pair) for pair in villages[key]]
                    replaced += 1
    gaz["_note"] = ("Master location data used for validation. District/tehsil names are real. "
                    "Village English names and LGD codes are real, from the Ministry of Panchayati "
                    "Raj's Local Government Directory (lgdirectory.gov.in, via a community CSV mirror, "
                    "2022 snapshot - see master/lgd_villages.csv). Village Hindi spellings are filled in "
                    "by transliterate.py, a rule-based approximation that is NOT verified against "
                    "official local-script spelling (see build_gazetteer.py / transliterate.py docstrings) "
                    "- treat them as unverified until a native speaker reviews them.")
    GAZETTEER.write_text(json.dumps(gaz, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"replaced villages for {replaced} tehsils")


if __name__ == "__main__":
    main()
