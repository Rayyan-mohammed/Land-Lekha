"""Measure the land-document classifier: does it keep land records in and everything else out?

    python eval/classify_eval.py

Land pages: every cached OCR page of the dev, test and multi splits (data/generated/<split>/ocr),
which are real OCR readings of 110 varied pages - four states, three layouts, printed and
handwritten fonts, scans, faded paper and phone photos. Non-land pages: datasets/non_land/,
OCR'd the same way (rebuild them with datasets/build_non_land.py).

The classifier never sees ground truth; it sees the OCR text, the page's quality verdict and
whether the quality check called it blurred - exactly what processing.py hands it. Writes
eval/results/classification.md.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.classify import classify  # noqa: E402

ORDER = {"poor": 0, "fair": 1, "good": 2}


def page_text(ocr: dict) -> tuple[str, int, str, bool]:
    lines = [l["text"] for pg in ocr.get("pages", []) for l in pg.get("lines", [])]
    hints = [pg["text_layer"] for pg in ocr.get("pages", []) if pg.get("text_layer")]
    text = "\n".join(lines + hints)
    quality = "good"
    for pg in ocr.get("pages", []):
        v = pg.get("quality", {}).get("verdict", "good")
        if ORDER.get(v, 2) < ORDER.get(quality, 2):
            quality = v
    blurred = any("blurred" in a for pg in ocr.get("pages", []) for a in pg.get("quality", {}).get("advice", []))
    return text, len(text.split()), quality, blurred


def profiles() -> dict[str, str]:
    """clean / scan / old / photo, from the evaluation results, which carry the generator's profile."""
    out = {}
    for split in ("dev", "test", "multi"):
        rp = ROOT / "eval" / "results" / f"{split}.json"
        if rp.exists():
            for d in json.loads(rp.read_text(encoding="utf-8"))["documents"]:
                out[d["id"]] = d.get("profile", "?")
    return out


def main() -> None:
    rows = []  # (truth_is_land, kind, name, verdict)
    prof = profiles()
    for split in ("dev", "test", "multi"):
        for cp in sorted((ROOT / "data" / "generated" / split / "ocr").glob("*.json")):
            text, words, quality, blurred = page_text(json.loads(cp.read_text(encoding="utf-8")))
            rows.append((True, f"land/{prof.get(cp.stem, '?')}", cp.stem,
                         classify(text, words=words, quality=quality, blurred=blurred)))
    for cp in sorted((ROOT / "datasets" / "non_land").glob("*/*.ocr.json")):
        text, words, quality, blurred = page_text(json.loads(cp.read_text(encoding="utf-8")))
        rows.append((False, f"non_land/{cp.parent.name}", cp.stem.replace(".ocr", ""),
                     classify(text, words=words, quality=quality, blurred=blurred)))

    tp = fp = tn = fn = 0
    by_kind: dict[str, Counter] = defaultdict(Counter)
    mistakes, undetermined = [], []
    for truth, kind, name, v in rows:
        if v.get("undetermined"):
            by_kind[kind]["undetermined"] += 1
            undetermined.append((kind, name, v["reason"]))
            continue
        said = v["is_land_document"]
        by_kind[kind]["land" if said else "not land"] += 1
        if truth and said:
            tp += 1
        elif truth and not said:
            fn += 1; mistakes.append((kind, name, "called NOT land", v["reason"]))
        elif not truth and said:
            fp += 1; mistakes.append((kind, name, "called land", v["reason"]))
        else:
            tn += 1
    decided = tp + fp + tn + fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / decided if decided else 0.0
    types = Counter(v["document_type"] for truth, _, _, v in rows if truth and v.get("is_land_document"))
    n_land = sum(1 for r in rows if r[0]); n_non = len(rows) - n_land

    lines = [
        "# Land-document classification",
        "",
        f"{n_land} land pages (real OCR readings of the dev, test and multi splits) and {n_non} non-land pages",
        "(`datasets/non_land/`, synthetic, no real person's document), classified from their OCR text exactly as",
        "`processing.py` does it. A page the quality check calls unreadable is *undetermined*: it goes back for a",
        "retake with no fields, and is not counted as a decision either way.",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Accuracy (decided pages) | **{accuracy:.1%}** ({tp + tn} of {decided}) |",
        f"| Precision - of pages called land, how many are | **{precision:.1%}** |",
        f"| Recall - of land pages, how many were kept | **{recall:.1%}** |",
        f"| F1 | **{f1:.3f}** |",
        f"| Undetermined (unreadable, sent for retake) | {len(undetermined)} |",
        "",
        "Confusion matrix (rows: truth, columns: verdict):",
        "",
        "| | called land | called not land |",
        "| --- | --- | --- |",
        f"| land page | {tp} | {fn} |",
        f"| not a land page | {fp} | {tn} |",
        "",
        "## By kind of page",
        "",
        "| Kind | pages | called land | called not land | undetermined |",
        "| --- | --- | --- | --- | --- |",
    ]
    for kind in sorted(by_kind):
        c = by_kind[kind]
        lines.append(f"| {kind} | {sum(c.values())} | {c['land']} | {c['not land']} | {c['undetermined']} |")
    lines += ["", "## Document types named on the land pages", "", "| Type | pages |", "| --- | --- |"]
    lines += [f"| {t} | {n} |" for t, n in types.most_common()]
    lines += ["", "## Undetermined pages", ""]
    lines += [f"- {k} / {n}: {r}" for k, n, r in undetermined] or ["None."]
    lines += ["", "## Mistakes", ""]
    if mistakes:
        lines += ["| Kind | Page | Verdict | Reason given |", "| --- | --- | --- | --- |"]
        lines += [f"| {k} | {n} | {s} | {r} |" for k, n, s, r in mistakes]
    else:
        lines.append("None on this data.")
    lines += ["", "The non-land set is small and synthetic; it shows the mechanism works, not that it is finished.",
              "Reproduce: `python eval/classify_eval.py`. The classifier is a rule ensemble over kinds of",
              "evidence (`backend/classify/land.py`); the numbers above are its own decisions, not a fit."]
    out = ROOT / "eval" / "results" / "classification.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
