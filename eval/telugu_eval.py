"""Build a small Telugu Pahani set with typed ground truth, and score the pipeline on it.

    python eval/telugu_eval.py --build --count 6      # write pages + ground truth
    python eval/telugu_eval.py                        # read them and score

Generated pages, deliberately: they prove the reader routing, the Telugu labels and the unit
table work end to end. They are not real Telangana paper and the results file says so.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data" / "generated" / "telugu"
FONT = "C:/Windows/Fonts/Nirmala.ttc"   # any font with Telugu coverage

VILLAGES = ["కొత్తపల్లి", "నార్సింగి", "మంచిరేవుల", "పెద్ద అంబర్‌పేట", "గుండ్లపోచంపల్లి"]
MANDALS = ["ఇబ్రహీంపట్నం", "శేరిలింగంపల్లి", "రాజేంద్రనగర్", "కీసర", "మేడ్చల్"]
NAMES = ["రమేష్ కుమార్", "లక్ష్మీ దేవి", "వెంకట్ రావు", "సునీత రెడ్డి", "అంజయ్య గౌడ్"]
FATHERS = ["నరసింహ రావు", "శ్రీనివాస్", "రాములు", "కృష్ణ మూర్తి", "బాలయ్య"]
SCORED = ["khata_number", "survey_number", "owner_name", "father_name", "plot_area"]


def build(count: int, font_path: str, seed: int = 4) -> None:
    from PIL import Image, ImageDraw, ImageFont

    OUT.mkdir(parents=True, exist_ok=True)
    random.seed(seed)
    for i in range(count):
        truth = {
            "village": VILLAGES[i % len(VILLAGES)], "tehsil": MANDALS[i % len(MANDALS)],
            "district": "రంగారెడ్డి", "state": "తెలంగాణ",
            "owner_name": NAMES[i % len(NAMES)], "father_name": FATHERS[i % len(FATHERS)],
            "khata_number": f"{random.randint(100, 9999):05d}",
            "survey_number": f"{random.randint(10, 499)}/{random.randint(1, 9)}",
            "plot_area": f"{random.choice(['0.80', '1.25', '2.40', '3.10'])} ఎకరం",
        }
        lines = [("పహాణీ / ADANGAL", 34),
                 (f"గ్రామం : {truth['village']}    మండలం : {truth['tehsil']}", 28),
                 (f"జిల్లా : {truth['district']}    రాష్ట్రం : {truth['state']}", 28),
                 (f"పట్టాదారు పేరు : {truth['owner_name']}", 28),
                 (f"తండ్రి పేరు : {truth['father_name']}", 28),
                 (f"ఖాతా సంఖ్య : {truth['khata_number']}", 28),
                 (f"సర్వే నంబరు : {truth['survey_number']}", 28),
                 (f"విస్తీర్ణం : {truth['plot_area']}", 28),
                 ("భూమి రకం : వ్యవసాయ (నీటిపారుదల)", 28)]
        img = Image.new("L", (1240, 760), 252)
        d, y = ImageDraw.Draw(img), 50
        for text, size in lines:
            d.text((70, y), text, font=ImageFont.truetype(font_path, size), fill=25)
            y += 72
        name = f"te-{i + 1:03d}"
        img.save(OUT / f"{name}.png")
        (OUT / f"{name}.json").write_text(
            json.dumps({"id": name, "script": "Telugu", "fields": truth}, ensure_ascii=False, indent=1),
            encoding="utf-8")
    print(f"wrote {count} pages to {OUT}")


def score() -> None:
    from backend.extraction.extractor import extract
    from backend.ocr.pipeline import run_ocr
    from backend.ocr.scripts import detect_scripts

    metas = sorted(OUT.glob("te-*.json"))
    if not metas:
        sys.exit(f"no pages in {OUT} - run with --build first")
    rows, t0 = [], time.perf_counter()
    for meta in metas:
        truth = json.loads(meta.read_text(encoding="utf-8"))
        ocr = run_ocr(meta.with_suffix(".png").read_bytes(), meta.stem + ".png")
        page = ocr["pages"][0]
        got = {k: v.get("value") for k, v in extract(ocr)["fields"].items()}
        hits = sum(1 for k in SCORED
                   if got.get(k) and str(truth["fields"][k]).split()[0] in str(got[k]))
        rows.append({
            "id": truth["id"], "reader": page["preprocess"].get("reader"),
            "scripts": detect_scripts(chr(10).join(l["text"] for l in page["lines"])),
            "hits": hits, "places": sum(1 for k in ("tehsil", "district", "state") if got.get(k)),
            "seconds": round(ocr["elapsed_ms"] / 1000, 1),
        })
    n = len(rows)
    print(f"{'page':8} {'reader':10} {'script':10} {'fields':>7} {'places':>7} {'seconds':>8}")
    for r in rows:
        print(f"{r['id']:8} {'+'.join(r['reader'] or []):10} {(r['scripts'] or ['-'])[0]:10} "
              f"{r['hits']}/{len(SCORED):<5} {r['places']}/3{'':4} {r['seconds']:7.1f}")
    fields = sum(r["hits"] for r in rows)
    print(f"\nreader chosen correctly : {sum(1 for r in rows if r['reader'] == ['te', 'en'])}/{n}")
    print(f"script named correctly  : {sum(1 for r in rows if r['scripts'][:1] == ['Telugu'])}/{n}")
    print(f"typed fields recovered  : {fields}/{n * len(SCORED)} = {fields / (n * len(SCORED)):.1%}")
    print(f"place names resolved    : {sum(r['places'] for r in rows)}/{3 * n}")
    print(f"wall clock              : {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true", help="write the pages and their ground truth")
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--font", default=FONT, help="a font with Telugu coverage")
    args = ap.parse_args()
    build(args.count, args.font) if args.build else score()
