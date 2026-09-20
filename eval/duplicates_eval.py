"""Does duplicate detection find the same parcel when it is read twice?

    python eval/duplicates_eval.py --split test

The real case is not two identical files - the upload check catches those by hash. It is the
same parcel arriving again as a different photograph, read slightly differently. So each
document's *ground truth* stands in for the record already in the register, and what the
pipeline actually extracted from the page stands in for the record arriving now, OCR errors
and all.

Positives: the extracted record against its own ground truth - must be found.
Negatives: the same extracted record against every other document's ground truth - must not be.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def records(split: str, cache: str = "ocr"):
    from backend.extraction.extractor import extract

    split_dir = ROOT / "data" / "generated" / split
    for meta_path in sorted(split_dir.glob(f"{split}-*.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        cached = split_dir / cache / f"{meta.get('id', meta_path.stem)}.json"
        if not cached.exists():
            continue
        gt = meta["fields"]
        stored = {"record_id": meta_path.stem, "district": gt.get("district"), "village": gt.get("village"),
                  "khata_number": gt.get("khata_number"), "khasra_number": gt.get("khasra_number"),
                  "owner_name": gt.get("owner_name"),
                  "parcels": [{"khasra_number": p.get("khasra_number")} for p in (gt.get("parcels") or [])],
                  "owners": [{"owner_name": o.get("owner_name")} for o in (gt.get("owners") or [])]}
        ext = extract(json.loads(cached.read_text(encoding="utf-8")))
        incoming = {k: (v or {}).get("value") for k, v in ext["fields"].items()}
        incoming["parcels"] = ext.get("parcels") or []
        incoming["owners"] = ext.get("owners") or []
        yield meta_path.stem, stored, incoming


def main() -> None:
    from backend.extraction.duplicates import find_duplicates

    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--cache", default="ocr")
    args = ap.parse_args()

    rows = list(records(args.split, args.cache))
    if not rows:
        sys.exit(f"no cached readings for split '{args.split}'")

    found, missed, false_hits = 0, [], []
    for name, stored, incoming in rows:
        if find_duplicates(incoming, [stored]):
            found += 1
        else:
            missed.append(name)
        others = [s for other, s, _ in rows if other != name]
        for hit in find_duplicates(incoming, others):
            false_hits.append((name, hit["record_id"], hit["score"], hit["reasons"]))

    n = len(rows)
    comparisons = n * (n - 1)
    print(f"{n} documents on the {args.split} split\n")
    print(f"the same parcel, read again : found {found}/{n} = {found / n:.1%}")
    print(f"different parcels           : {len(false_hits)} false matches in {comparisons} comparisons")
    if missed:
        print(f"\nnot recognised ({len(missed)}): {', '.join(missed[:10])}")
    for a, b, score, reasons in false_hits[:5]:
        print(f"  false match {a} ~ {b} at {score}: {reasons}")


if __name__ == "__main__":
    main()
