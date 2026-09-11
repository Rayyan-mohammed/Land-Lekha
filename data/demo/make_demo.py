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
    ("06-scanned-pdf", lambda m: any(f.endswith(".pdf") for f in m["files"])),
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
    (DEMO / "expected.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
