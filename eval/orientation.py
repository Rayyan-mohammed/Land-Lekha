"""Does the pipeline recover pages photographed sideways or upside down?

    python eval/orientation.py --split dev --docs 6

Takes documents that read well upright, rotates the original image by 90/180/270
degrees, runs the full OCR + extraction pipeline and compares field accuracy with the
upright result (from the OCR cache). Writes eval/results/orientation.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from backend.extraction.extractor import extract  # noqa: E402
from backend.ocr.pipeline import run_ocr  # noqa: E402
from evaluate import field_correct  # noqa: E402

ROTATIONS = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}


def accuracy(ext: dict, gt: dict) -> float:
    return sum(field_correct(n, ext["fields"].get(n), v) for n, v in gt.items()) / len(gt)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--docs", type=int, default=6)
    args = ap.parse_args()
    split_dir = ROOT / "data" / "generated" / args.split

    # documents that read well upright, one per template where possible
    picked, seen = [], {}
    for mp in sorted(split_dir.glob(f"{args.split}-*.json")):
        meta = json.loads(mp.read_text(encoding="utf-8"))
        cache = split_dir / "ocr" / mp.name
        if not cache.exists():
            continue
        acc = accuracy(extract(json.loads(cache.read_text(encoding="utf-8"))), meta["fields"])
        if acc >= 0.9 and seen.get(meta["template"], 0) < (args.docs + 2) // 3:
            picked.append((meta, acc))
            seen[meta["template"]] = seen.get(meta["template"], 0) + 1
        if len(picked) >= args.docs:
            break

    rows, ok_orient, total = [], 0, 0
    for meta, base in picked:
        img = cv2.imread(str(split_dir / f"{meta['id']}.png"))
        line = [meta["id"], meta["template"], f"{base:.0%}"]
        for deg, code in ROTATIONS.items():
            _, enc = cv2.imencode(".png", cv2.rotate(img, code))
            ocr = run_ocr(enc.tobytes(), "rotated.png")
            acc = accuracy(extract(ocr), meta["fields"])
            steps = ocr["pages"][0]["preprocess"]["steps"]
            fixed = acc >= base - 0.1
            ok_orient += fixed
            total += 1
            line.append(f"{acc:.0%} ({'+'.join(s for s in steps if s.startswith('rotate')) or 'none'})")
            print(meta["id"], deg, f"{acc:.0%}", steps)
        rows.append(line)

    md = ["# Orientation recovery", "",
          f"Pages that read well upright, rotated and re-processed end to end. "
          f"**{ok_orient}/{total}** rotated pages recovered to within 10 points of their upright field accuracy.", "",
          "| Document | Template | Upright | 90° | 180° | 270° |", "| --- | --- | --- | --- | --- | --- |"]
    md += ["| " + " | ".join(r) + " |" for r in rows]
    md += ["", "In brackets: the rotation steps the pipeline applied (`rotate90` from the text-line projection test, "
           "`rotate180` from the recognition-confidence check)."]
    (ROOT / "eval" / "results" / "orientation.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{ok_orient}/{total} recovered")


if __name__ == "__main__":
    main()
