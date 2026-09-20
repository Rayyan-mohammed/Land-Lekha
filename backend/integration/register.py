"""A stand-in for a state land register, and the comparison against it.

**This is simulated.** No state gives us an API, so the register here is a local table seeded
from the same LGD villages the rest of the system uses. Every response it produces is marked
`"simulated": true`, and nothing in the UI or the docs may describe a match against it as
proof that a document is genuine. What it demonstrates is the mechanism: given a record we
just read off a page, look it up in an external register and show, field by field, where the
two agree and where they do not.

Why that matters more than it sounds: a record can be read perfectly and still be wrong - the
paper itself can be out of date, or the parcel may have been mutated since. Comparing against
the register is the only check that can catch that, and it is the one a tehsildar actually
performs by hand today.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

STORE = Path(os.getenv("LL_REGISTER_PATH", Path(__file__).resolve().parents[2] / "data" / "register.json"))

# Fields worth comparing, and how much a disagreement in each one matters. A different owner
# name is a question; a different khasra number means we are not looking at the same parcel.
COMPARED: dict[str, str] = {
    "khasra_number": "identifier",
    "khata_number": "identifier",
    "owner_name": "party",
    "father_name": "party",
    "plot_area": "measure",
    "land_classification": "measure",
    "village": "place",
    "tehsil": "place",
    "district": "place",
}


@dataclass
class Entry:
    """One row as the state register holds it."""
    key: str
    fields: dict
    source: str = "simulated state register"


@dataclass
class Register:
    entries: dict[str, Entry] = field(default_factory=dict)

    @staticmethod
    def key_for(village: str | None, khata: str | None, khasra: str | None) -> str:
        """How a clerk finds a parcel: village, then khata, then khasra."""
        return "|".join([(village or "?").strip().casefold(), (khata or "?").strip(), (khasra or "?").strip()])

    def add(self, fields: dict) -> Entry:
        key = self.key_for(fields.get("village"), fields.get("khata_number"), fields.get("khasra_number"))
        entry = Entry(key=key, fields={k: v for k, v in fields.items() if k in COMPARED})
        self.entries[key] = entry
        return entry

    def find(self, fields: dict) -> Entry | None:
        """Look the parcel up the way a clerk would: village, khata, khasra."""
        return self.entries.get(self.key_for(fields.get("village"), fields.get("khata_number"),
                                             fields.get("khasra_number")))

    def save(self, path: Path | None = None) -> None:
        path = path or STORE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({k: e.fields for k, e in self.entries.items()}, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    @classmethod
    def load(cls, path: Path | None = None) -> "Register":
        path = path or STORE
        reg = cls()
        if path.exists():
            for key, fields in json.loads(path.read_text(encoding="utf-8")).items():
                reg.entries[key] = Entry(key=key, fields=fields)
        return reg


def compare(extracted: dict, entry: Entry | None) -> dict:
    """Field by field, does what we read match what the register holds?

    `extracted` is the flat {name: value} of the record we read. Values are compared as
    written, case- and space-insensitively; nothing is corrected or overwritten here. A field
    the register does not carry is reported as `not_held`, not as a disagreement."""
    if entry is None:
        return {"simulated": True, "found": False, "agree": 0, "differ": 0, "fields": {},
                "summary": "no matching parcel in the register"}

    def same(a, b) -> bool:
        return " ".join(str(a).split()).casefold() == " ".join(str(b).split()).casefold()

    out, agree, differ = {}, 0, 0
    for name, kind in COMPARED.items():
        mine, theirs = extracted.get(name), entry.fields.get(name)
        if mine is None or theirs is None:
            out[name] = {"status": "not_held", "ours": mine, "register": theirs, "kind": kind}
            continue
        if same(mine, theirs):
            out[name] = {"status": "agree", "ours": mine, "register": theirs, "kind": kind}
            agree += 1
        else:
            out[name] = {"status": "differ", "ours": mine, "register": theirs, "kind": kind}
            differ += 1
    summary = ("matches the register" if differ == 0 else
               f"{differ} field{'s' if differ != 1 else ''} differ from the register")
    return {"simulated": True, "found": True, "agree": agree, "differ": differ,
            "fields": out, "summary": summary}
