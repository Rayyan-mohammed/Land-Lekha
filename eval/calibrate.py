"""Fit the field-confidence calibrator on the dev split.

    python eval/calibrate.py --split dev [--target-precision 0.98]

For every extracted field on the dev documents we know whether it was right (from
ground truth). A logistic regression learns P(correct | features) and the
auto-accept threshold is the lowest confidence at which fields above it are at
least `target-precision` correct on dev. Writes backend/extraction/master/calibration.json.

Evaluate on the *test* split afterwards (eval/evaluate.py --split test) — never
calibrate and report on the same split.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from backend.extraction import confidence  # noqa: E402
from backend.extraction.confidence import CALIBRATION, FEATURES, features  # noqa: E402
from backend.extraction.extractor import extract  # noqa: E402
from evaluate import field_correct, scalar_fields  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--target-precision", type=float, default=0.98)
    args = ap.parse_args()

    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_predict

    # extract with the heuristic formula so the features don't depend on an old calibration
    if CALIBRATION.exists():
        CALIBRATION.unlink()
    confidence.calibration.cache_clear()

    split_dir = ROOT / "data" / "generated" / args.split
    X, y, names = [], [], []
    for cp in sorted((split_dir / "ocr").glob("*.json")):
        meta = json.loads((split_dir / cp.name).read_text(encoding="utf-8"))
        ext = extract(json.loads(cp.read_text(encoding="utf-8")))
        for name, f in ext["fields"].items():
            X.append(features(name, f))
            gt = scalar_fields(meta)
            y.append(int(name in gt and field_correct(name, f, gt[name])))
            names.append(name)
    X, y = np.array(X), np.array(y)
    print(f"{len(y)} fields from {args.split}, {y.mean():.1%} correct")

    model = LogisticRegression(C=1.0, max_iter=2000)
    # out-of-fold probabilities to pick the threshold honestly
    p_oof = cross_val_predict(model, X, y, cv=5, method="predict_proba")[:, 1]
    model.fit(X, y)

    threshold = 0.95
    for t in np.arange(0.50, 0.99, 0.01):
        sel = p_oof >= t
        if sel.sum() >= 10 and y[sel].mean() >= args.target_precision:
            threshold = float(round(t, 2))
            break
    sel = p_oof >= threshold
    print(f"threshold {threshold}: {sel.mean():.1%} of fields above it, {y[sel].mean():.1%} of those correct")
    print("raw OCR confidence alone, same coverage:",
          f"{y[np.argsort(-X[:, 0])[: sel.sum()]].mean():.1%} correct")

    cal = {
        "features": FEATURES,
        "coef": [round(float(c), 5) for c in model.coef_[0]],
        "intercept": round(float(model.intercept_[0]), 5),
        "threshold": threshold,
        "target_precision": args.target_precision,
        "trained_on": args.split,
        "n_fields": int(len(y)),
        "base_accuracy": round(float(y.mean()), 4),
    }
    CALIBRATION.write_text(json.dumps(cal, indent=1), encoding="utf-8")
    confidence.calibration.cache_clear()
    for f, c in sorted(zip(FEATURES, cal["coef"]), key=lambda t: -abs(t[1])):
        print(f"  {f:14s} {c:+.3f}")
    print(f"wrote {CALIBRATION.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
