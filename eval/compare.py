"""A/B-compare two OCR settings on the same documents, with the same extraction code.

    python eval/compare.py --split dev ocr ocr_c1024

Each argument after --split is an OCR cache folder under data/generated/<split>/
(written by eval/evaluate.py --cache NAME). Only documents present in every cache
are compared. Prints CER, field accuracy and OCR time, overall and per page type.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from backend.extraction.extractor import extract  # noqa: E402
from evaluate import cer, field_correct, scalar_fields  # noqa: E402


def score(split_dir: Path, cache: str, ids: list[str]) -> dict:
    out = {"cer": [], "fields": [0, 0], "ms": [], "by": defaultdict(lambda: [0, 0])}
    for did in ids:
        meta = json.loads((split_dir / f"{did}.json").read_text(encoding="utf-8"))
        ocr = json.loads((split_dir / cache / f"{did}.json").read_text(encoding="utf-8"))
        ext = extract(ocr)
        out["cer"].append(cer("\n".join(l["text"] for p in ocr["pages"] for l in p["lines"]), meta["text"]))
        out["ms"].append(ocr["elapsed_ms"])
        for name, gt in scalar_fields(meta).items():
            ok = int(field_correct(name, ext["fields"].get(name), gt))
            out["fields"][0] += ok
            out["fields"][1] += 1
            for g in (meta["degradation"]["profile"], meta["template"]):
                out["by"][g][0] += ok
                out["by"][g][1] += 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("caches", nargs="+")
    args = ap.parse_args()
    split_dir = ROOT / "data" / "generated" / args.split
    sets = [{p.stem for p in (split_dir / c).glob("*.json")} for c in args.caches]
    ids = sorted(set.intersection(*sets))
    print(f"{len(ids)} documents in common")
    results = {c: score(split_dir, c, ids) for c in args.caches}
    groups = sorted({g for r in results.values() for g in r["by"]})
    print(f"{'':22s}" + "".join(f"{c:>14s}" for c in args.caches))
    rows = [("field accuracy", lambda r: f"{r['fields'][0] / r['fields'][1]:.1%}"),
            ("CER median", lambda r: f"{statistics.median(r['cer']):.1%}"),
            ("CER mean", lambda r: f"{statistics.mean(r['cer']):.1%}"),
            ("OCR s/doc (median)", lambda r: f"{statistics.median(r['ms']) / 1000:.1f}")]
    rows += [(f"  {g}", lambda r, g=g: f"{r['by'][g][0] / max(1, r['by'][g][1]):.1%}") for g in groups]
    for label, fn in rows:
        print(f"{label:22s}" + "".join(f"{fn(results[c]):>14s}" for c in args.caches))


if __name__ == "__main__":
    main()
