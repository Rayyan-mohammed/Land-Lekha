"""Build the small, committed demo document set (data/demo/).

    python data/demo/make_demo.py

Generates a fixed-seed batch, picks one document of each kind we want to show
live, stores them as JPEG / PDF (small enough to commit) and writes expected.md
with the ground truth, so the presenter knows what the right answer is.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "data" / "demo"
SRC = ROOT / "data" / "generated" / "demo"

PICKS = [
    ("01-ror-english-clean", lambda m: m["template"] == "ror_english" and m["degradation"]["profile"] == "clean"),
    ("02-khatauni-table-scan", lambda m: m["template"] == "khatauni_table" and m["degradation"]["profile"] == "scan"),
    ("03-form-handwritten", lambda m: m["template"] == "form_bilingual" and m["handwritten"]),
    ("04-old-faded-record", lambda m: m["degradation"]["profile"] == "old"),
    ("05-phone-photo", lambda m: m["degradation"]["profile"] == "photo"),
    ("06-scanned-pdf", lambda m: m["degradation"]["profile"] == "scan" and any(f.endswith(".pdf") for f in m["files"])),
]


def main() -> None:
    if not SRC.exists() or len(list(SRC.glob("*.json"))) < 24:
        subprocess.run([sys.executable, str(ROOT / "data/generator/generate.py"), "--count", "24", "--split", "demo",
                        "--seed", "26018", "--pdf-ratio", "0.25"], check=True)
    metas = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(SRC.glob("demo-*.json"))]
    used, lines = set(), ["# Demo documents — expected values", "",
                          "Ground truth for each demo file (generated with seed 26018).", ""]
    for name, pred in PICKS:
        m = next((m for m in metas if m["id"] not in used and pred(m)), None)
        if m is None:
            print(f"no document for {name}")
            continue
        used.add(m["id"])
        if name.endswith("pdf"):
            out = DEMO / f"{name}.pdf"
            shutil.copy(SRC / f"{m['id']}.pdf", out)
        else:
            out = DEMO / f"{name}.jpg"
            cv2.imwrite(str(out), cv2.imread(str(SRC / f"{m['id']}.png")), [cv2.IMWRITE_JPEG_QUALITY, 90])
        lines += [f"## {out.name}", f"{m['template']} · {m['degradation']['profile']} · handwritten={m['handwritten']}", "",
                  "| Field | Expected |", "| --- | --- |"]
        for k, v in m["fields"].items():
            if k == "plot_area":
                v = f"{v['value']} {v['unit']} ({v['hectares']} ha)"
            lines.append(f"| {k} | {v} |")
        lines.append("")
        print(f"{out.name:32s} <- {m['id']}  {out.stat().st_size // 1024} KB")
    lines += extras()
    (DEMO / "expected.md").write_text("\n".join(lines), encoding="utf-8")


def _table(fields: dict) -> list[str]:
    out = ["| Field | Expected |", "| --- | --- |"]
    for k, v in fields.items():
        if k == "plot_area":
            v = f"{v['value']} {v['unit']} ({v['hectares']} ha)"
        elif k == "owners":
            v = "; ".join(o["owner_name"] + (f" (s/o {o['father_name']})" if o.get("father_name") else "") for o in v)
        elif k == "parcels":
            v = "; ".join(f"{p['khasra_number']} = {p['plot_area']['value']} {p['plot_area']['unit']}, {p['land_classification']}"
                          for p in v)
        out.append(f"| {k} | {v} |")
    return out + [""]


def extras() -> list[str]:
    """Samples for today's capabilities: sideways photo, born-digital PDF, multi-owner khata."""
    sys.path.insert(0, str(ROOT / "data" / "generator"))
    import random

    import generate as g
    from playwright.sync_api import sync_playwright

    lines = []
    # 07: the clean English record photographed sideways -> auto-rotated
    first = json.loads((SRC / "demo-023.json").read_text(encoding="utf-8"))
    img = cv2.imread(str(SRC / "demo-023.png"))
    out = DEMO / "07-sideways-photo.jpg"
    cv2.imwrite(str(out), cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE), [cv2.IMWRITE_JPEG_QUALITY, 90])
    lines += [f"## {out.name}", "Same record as 01, photographed sideways: the pipeline turns it upright (`rotate90`).", ""]
    lines += _table(first["fields"])
    print(f"{out.name:32s} <- demo-023 rotated  {out.stat().st_size // 1024} KB")

    # 08 + 09: a born-digital PDF and a multi-owner Khatauni, freshly rendered
    g.ensure_fonts()
    gaz = json.loads(g.GAZETTEER.read_text(encoding="utf-8"))
    rng = random.Random(26018)
    css = (g.BASE_CSS.replace("FONTDIR", g.FONT_DIR.resolve().as_uri()).replace("PAGEW", str(g.PAGE_W))
           .replace("PAGEH", str(g.PAGE_H)))
    tmp = DEMO / "_render.html"
    with sync_playwright() as p:
        browser = g.launch(p)
        page = browser.new_page(viewport={"width": g.PAGE_W, "height": g.PAGE_H})

        def render(body: str, font: str):
            tmp.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{css.replace('BODYFONT', font)}</style>"
                           f"</head><body>{body}</body></html>", encoding="utf-8")
            page.goto(tmp.resolve().as_uri())
            page.evaluate("document.fonts.ready")

        rec = g.make_record(rng, gaz)
        render(g.tpl_form_bilingual(rec, rng, False, False), "Hind")
        out = DEMO / "08-born-digital.pdf"
        page.pdf(path=str(out), width=f"{g.PAGE_W}px", height=f"{g.PAGE_H}px", print_background=True)
        lines += [f"## {out.name}", "Exported by a portal (real text inside): read from the text layer in about a second, no OCR.", ""]
        lines += _table(g.ground_truth(rec, "hi"))
        print(f"{out.name:32s} <- rendered as a digital PDF  {out.stat().st_size // 1024} KB")

        while True:
            rec = g.make_record(rng, gaz, multi=True)
            if len(rec.owners) >= 3 and len(rec.parcels) >= 2:
                break
        render(g.tpl_khatauni_table(rec, rng, False, False), "Hind")
        png = page.screenshot()
        browser.close()
    tmp.unlink(missing_ok=True)
    import numpy as np

    shot = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
    deg, _, _ = g.degrade(shot, "scan", rng)
    out = DEMO / "09-multi-owner-khatauni.jpg"
    cv2.imwrite(str(out), deg, [cv2.IMWRITE_JPEG_QUALITY, 90])
    lines += [f"## {out.name}", f"One khata, {len(rec.owners)} co-owners and {len(rec.parcels)} khasra rows.", ""]
    lines += _table(g.ground_truth(rec, "hi"))
    print(f"{out.name:32s} <- rendered multi-owner khatauni  {out.stat().st_size // 1024} KB")
    return lines


if __name__ == "__main__":
    main()
