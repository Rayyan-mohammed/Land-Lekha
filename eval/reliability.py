"""Is the confidence number honest? Expected calibration error and a risk-coverage curve.

    python eval/reliability.py --split test

"Confidence 0.9" should mean "right about nine times in ten". This checks that, using the
cached OCR readings and the same definition of a correct field as eval/evaluate.py, so the
numbers can be compared with the ones in test.md.

Two things come out:

* **Reliability table / ECE.** Fields are put in confidence bins; each bin's mean confidence
  is compared with how often it was actually right. The expected calibration error is the
  average gap, weighted by how many fields fall in each bin. Small is good.
* **Risk-coverage.** If we accept only fields above a threshold, what share do we accept
  (coverage) and what share of those are wrong (risk)? This is the curve behind the choice of
  operating point, and it shows what the threshold buys.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.evaluate import field_correct  # noqa: E402  same definition, deliberately


def pairs(split: str, cache: str = "ocr") -> list[tuple[str, float, bool]]:
    """(field name, confidence, was it right) for every field extracted on the split."""
    from backend.extraction.extractor import extract

    split_dir = ROOT / "data" / "generated" / split
    out = []
    for meta_path in sorted(split_dir.glob(f"{split}-*.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        cached = split_dir / cache / f"{meta.get('id', meta_path.stem)}.json"
        if not cached.exists():
            continue
        gt = meta.get("fields", meta)
        ext = extract(json.loads(cached.read_text(encoding="utf-8")))
        for name, f in ext["fields"].items():
            if f.get("value") is None:
                continue
            out.append((name, float(f["confidence"]), bool(name in gt and field_correct(name, f, gt[name]))))
    return out


def reliability(data, bins: int = 10):
    """Mean confidence against observed accuracy, per bin, plus the ECE."""
    rows, n = [], len(data)
    ece = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        chunk = [d for d in data if (lo <= d[1] < hi or (b == bins - 1 and d[1] == 1.0))]
        if not chunk:
            continue
        mean_conf = sum(c for _, c, _ in chunk) / len(chunk)
        acc = sum(ok for _, _, ok in chunk) / len(chunk)
        ece += len(chunk) / n * abs(mean_conf - acc)
        rows.append({"bin": f"{lo:.1f}-{hi:.1f}", "fields": len(chunk),
                     "mean_confidence": round(mean_conf, 3), "accuracy": round(acc, 3),
                     "gap": round(acc - mean_conf, 3)})
    return rows, ece


def risk_coverage(data, steps=(0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95)):
    """Accept only fields at or above each threshold: how many, and how many of them wrong."""
    rows = []
    for t in steps:
        kept = [d for d in data if d[1] >= t]
        if not kept:
            continue
        wrong = sum(1 for _, _, ok in kept if not ok)
        rows.append({"threshold": t, "coverage": round(len(kept) / len(data), 3),
                     "accepted": len(kept), "wrong": wrong,
                     "risk": round(wrong / len(kept), 4)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--cache", default="ocr")
    ap.add_argument("--bins", type=int, default=10)
    args = ap.parse_args()

    data = pairs(args.split, args.cache)
    if not data:
        sys.exit(f"no cached readings for split '{args.split}'")
    rows, ece = reliability(data, args.bins)

    print(f"{len(data)} extracted fields on the {args.split} split\n")
    print(f"{'confidence':12} {'fields':>7} {'mean conf':>10} {'actually right':>15} {'gap':>7}")
    for r in rows:
        print(f"{r['bin']:12} {r['fields']:7} {r['mean_confidence']:10.3f} {r['accuracy']:15.3f} {r['gap']:+7.3f}")
    print(f"\nexpected calibration error: {ece:.4f}")

    print(f"\n{'threshold':>10} {'coverage':>9} {'accepted':>9} {'wrong':>6} {'risk':>8}")
    for r in risk_coverage(data):
        print(f"{r['threshold']:10.2f} {r['coverage']:9.3f} {r['accepted']:9} {r['wrong']:6} {r['risk']:8.4f}")


if __name__ == "__main__":
    main()
