"""Measure LandLekha on real documents, reported apart from the synthetic numbers.

    python eval/real_eval.py

Reads every image or PDF in data/real/ that has a matching JSON of typed ground truth (format:
data/real/README.md). Runs the full pipeline - OCR, document type, extraction - and scores it
with the same definition of a correct field as eval/evaluate.py, so the two can be compared.

Privacy: the documents and their ground truth never leave this machine (data/real/ is ignored
by git). The report printed here and written to eval/results/real.md carries field names,
counts and document types - never a person's name or a value read off the page.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.evaluate import field_correct  # noqa: E402  same definition, deliberately

REAL = ROOT / "data" / "real"
EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp")


def documents():
    for meta_path in sorted(REAL.glob("*.json")):
        doc = next((meta_path.with_suffix(e) for e in EXTS if meta_path.with_suffix(e).exists()), None)
        if doc:
            yield doc, json.loads(meta_path.read_text(encoding="utf-8"))


def main() -> None:
    from backend.extraction.extractor import extract
    from backend.ocr.pipeline import run_ocr
    from backend.ocr.scripts import detect_scripts

    rows, per_field = [], Counter()
    for path, truth in documents():
        t0 = time.perf_counter()
        ocr = run_ocr(path.read_bytes(), path.name)
        ext = extract(ocr)
        seconds = time.perf_counter() - t0
        page = ocr["pages"][0]
        text = "\n".join(l["text"] for p in ocr["pages"] for l in p["lines"])
        hits = {}
        for name, gv in truth["fields"].items():
            ok = field_correct(name, ext["fields"].get(name), gv)
            hits[name] = ok
            per_field[(name, ok)] += 1
        rows.append({
            "id": truth["id"], "fields": len(hits), "correct": sum(hits.values()),
            "wrong": [n for n, ok in hits.items() if not ok],
            "type_truth": truth.get("document_type"), "type_read": ext["document_type"],
            "quality": page["quality"]["verdict"], "reader": "+".join(page["preprocess"].get("reader") or ["hi", "en"]),
            "scripts": detect_scripts(text), "route": ext["route"], "seconds": round(seconds, 1),
        })

    if not rows:
        sys.exit("no documents with ground truth in data/real/ - see data/real/README.md")

    total = sum(r["fields"] for r in rows)
    correct = sum(r["correct"] for r in rows)
    types_ok = sum(1 for r in rows if r["type_read"] == r["type_truth"])
    auto = sum(1 for r in rows if r["route"] == "auto_accept")

    lines = [f"{len(rows)} real documents, {total} typed fields\n",
             f"field accuracy        : {correct}/{total} = {correct / total:.1%}",
             f"document type correct : {types_ok}/{len(rows)}",
             f"auto-accepted         : {auto}/{len(rows)} (anything else went to a person)\n",
             f"{'document':18} {'quality':8} {'reader':7} {'fields':>7} {'type read':16} {'wrong':30}"]
    for r in rows:
        lines.append(f"{r['id']:18} {r['quality']:8} {r['reader']:7} {r['correct']}/{r['fields']:<5} "
                     f"{r['type_read'] or '-':16} {', '.join(r['wrong']) or '-'}")
    lines.append("\nper field (right / wrong):")
    for name in sorted({n for n, _ in per_field}):
        lines.append(f"  {name:20} {per_field[(name, True)]} / {per_field[(name, False)]}")
    print("\n".join(lines))
    (ROOT / "eval" / "results" / "real.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
