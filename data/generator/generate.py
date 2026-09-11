"""Synthetic land-record dataset generator.

Renders realistic Hindi / English land records (Khatauni-style table, bilingual
filled form with handwritten entries, English Record of Rights) in a real browser
engine (correct Devanagari shaping), then degrades them to look like scans or
phone photos. Every document gets exact ground truth: field values, field boxes
and full-text lines (for CER).

    python data/generator/generate.py --count 40 --split dev --seed 1
    python data/generator/generate.py --count 40 --split test --seed 2

Output: data/generated/<split>/<doc_id>.png + <doc_id>.json (+ .pdf for some docs)
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from names import FIRST_NAMES_F, FIRST_NAMES_M, MIDDLE, SURNAMES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GAZETTEER = ROOT / "backend" / "extraction" / "master" / "gazetteer.json"
FONT_DIR = ROOT / "data" / "fonts"
OUT_DIR = ROOT / "data" / "generated"

FONTS = {
    "Hind-Regular.ttf": "hind/Hind-Regular.ttf",
    "Hind-SemiBold.ttf": "hind/Hind-SemiBold.ttf",
    "Kalam-Regular.ttf": "kalam/Kalam-Regular.ttf",
    "TiroDevanagariHindi-Regular.ttf": "tirodevanagarihindi/TiroDevanagariHindi-Regular.ttf",
    "Martel-Regular.ttf": "martel/Martel-Regular.ttf",
}

DEV_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
PAGE_W, PAGE_H = 1240, 1754  # A4 @ 150 dpi

LAND_CLASS_TEXT = {
    "agricultural_irrigated": ("कृषि (सिंचित)", "Agricultural (Irrigated)"),
    "agricultural_unirrigated": ("कृषि (असिंचित)", "Agricultural (Unirrigated)"),
    "residential_abadi": ("आबादी", "Residential (Abadi)"),
    "barren": ("बंजर", "Barren"),
    "pasture": ("चरागाह", "Pasture"),
    "orchard": ("बाग", "Orchard"),
}
UNIT_TEXT = {"hectare": ("हेक्टेयर", "Hectare"), "acre": ("एकड़", "Acre"), "bigha": ("बीघा", "Bigha")}


def ensure_fonts() -> None:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for name, path in FONTS.items():
        dst = FONT_DIR / name
        if not dst.exists():
            url = f"https://github.com/google/fonts/raw/main/ofl/{path}"
            print(f"downloading font {name}")
            urllib.request.urlretrieve(url, dst)


# ---------------------------------------------------------------- record model

@dataclass
class Record:
    state: dict
    district: dict
    tehsil: dict
    village: tuple[str, str]
    owner: tuple[str, str]
    father: tuple[str, str] | None
    khata: str
    khasra: tuple[str, str]  # (hindi form, english form)
    survey: str | None
    area_value: float
    area_unit: str
    land_class: str
    mutation_no: str | None
    mutation_date: str | None
    reg_no: str | None
    reg_date: str | None
    extras: dict = field(default_factory=dict)
    # co-owners and parcel rows under one khata; owner/father/khasra/area_value/land_class
    # above always equal owners[0] / parcels[0], for callers that only know the single fields
    owners: list[tuple[tuple[str, str], tuple[str, str] | None]] = field(default_factory=list)
    parcels: list[dict] = field(default_factory=list)


def rand_date(rng: random.Random, start_year=1995, end_year=2024) -> str:
    d0 = date(start_year, 1, 1)
    d = d0 + timedelta(days=rng.randint(0, (date(end_year, 12, 31) - d0).days))
    return d.strftime("%d/%m/%Y")


def person(rng: random.Random, female: bool, surname=None) -> tuple[str, str]:
    first = rng.choice(FIRST_NAMES_F if female else FIRST_NAMES_M)
    mid = ("", "") if female else rng.choice(MIDDLE)
    sur = surname or rng.choice(SURNAMES)
    hi = " ".join(p for p in (first[0], mid[0], sur[0]) if p)
    en = " ".join(p for p in (first[1], mid[1], sur[1]) if p)
    return hi, en


def make_khasra(rng: random.Random) -> tuple[str, str]:
    base = rng.randint(1, 1999)
    style = rng.random()
    if style < 0.4:
        return str(base), str(base)
    if style < 0.8:
        sub = rng.randint(1, 9)
        return f"{base}/{sub}", f"{base}/{sub}"
    sub = rng.randint(1, 9)
    i = rng.randint(0, 2)
    return f"{base}/{sub}{'कखग'[i]}", f"{base}/{sub}{'ABC'[i]}"


def make_parcel(rng: random.Random, unit: str) -> dict:
    value = {"hectare": round(rng.uniform(0.05, 4.5), 3), "acre": round(rng.uniform(0.2, 10), 2),
             "bigha": round(rng.uniform(0.5, 20), 2)}[unit]
    return {"khasra": make_khasra(rng), "area_value": value, "land_class": rng.choice(list(LAND_CLASS_TEXT))}


def make_record(rng: random.Random, gaz: dict, multi: bool = False) -> Record:
    """`multi`: real Khataunis list several co-owners and several parcel rows under one
    khata. Set for the khatauni_table template only; other templates stay single-value."""
    state = rng.choice(gaz["states"])
    district = rng.choice(state["districts"])
    tehsil = rng.choice(district["tehsils"])
    village = tuple(rng.choice(tehsil["villages"]))
    surname = rng.choice(SURNAMES)

    n_owners = rng.randint(1, 3) if multi else 1
    owners = []
    for _ in range(n_owners):
        owner = person(rng, rng.random() < 0.3, surname)
        father = person(rng, False, surname) if rng.random() < 0.9 else None
        owners.append((owner, father))

    unit = {"UP": "hectare", "MP": "hectare", "RJ": "bigha", "BR": "bigha"}[state["code"]]
    if rng.random() < 0.2:
        unit = "acre"
    n_parcels = rng.randint(1, 4) if multi else 1
    parcels = [make_parcel(rng, unit) for _ in range(n_parcels)]

    has_mut = rng.random() < 0.8
    has_reg = rng.random() < 0.6
    return Record(
        state=state, district=district, tehsil=tehsil, village=village,
        owner=owners[0][0], father=owners[0][1],
        khata=f"{rng.randint(1, 1500):05d}" if rng.random() < 0.6 else str(rng.randint(1, 1500)),
        khasra=parcels[0]["khasra"],
        survey=f"{rng.randint(1, 450)}/{rng.randint(1, 6)}" if state["code"] in ("MP", "RJ") or rng.random() < 0.3 else None,
        area_value=parcels[0]["area_value"], area_unit=unit,
        land_class=parcels[0]["land_class"],
        mutation_no=str(rng.randint(100, 9999)) if has_mut else None,
        mutation_date=rand_date(rng) if has_mut else None,
        reg_no=f"{rng.randint(1995, 2024)}/{rng.randint(1, 99999):05d}" if has_reg else None,
        reg_date=rand_date(rng) if has_reg else None,
        extras={"fasli": f"{rng.randint(1420, 1432)}-{rng.randint(1433, 1440)}", "remark_no": rng.randint(1, 60)},
        owners=owners, parcels=parcels,
    )


def ground_truth(r: Record, script: str) -> dict:
    """Canonical expected values. Names keep the script they are written in."""
    hi = script == "hi"
    bigha_ha = r.state["bigha_ha"]
    to_ha = {"hectare": 1.0, "acre": 0.404686, "bigha": bigha_ha}[r.area_unit]
    gt = {
        "owner_name": r.owner[0] if hi else r.owner[1],
        "father_name": (r.father[0] if hi else r.father[1]) if r.father else None,
        "khata_number": r.khata,
        "khasra_number": r.khasra[0] if hi else r.khasra[1],
        "survey_number": r.survey,
        "plot_area": {"value": r.area_value, "unit": r.area_unit, "hectares": round(r.area_value * to_ha, 4)},
        "land_classification": r.land_class,
        "village": r.village[0],  # canonical english
        "tehsil": r.tehsil["en"],
        "district": r.district["en"],
        "state": r.state["en"],
        "mutation_number": r.mutation_no,
        "mutation_date": r.mutation_date,
        "registration_number": r.reg_no,
        "registration_date": r.reg_date,
        "owners": [{"owner_name": o[0] if hi else o[1], "father_name": (f[0] if hi else f[1]) if f else None}
                   for o, f in r.owners],
        "parcels": [{"khasra_number": p["khasra"][0] if hi else p["khasra"][1],
                     "plot_area": {"value": p["area_value"], "unit": r.area_unit,
                                   "hectares": round(p["area_value"] * to_ha, 4)},
                     "land_classification": p["land_class"]} for p in r.parcels],
    }
    return {k: v for k, v in gt.items() if v is not None}


# ---------------------------------------------------------------- templates

BASE_CSS = """
@font-face { font-family: Hind; src: url('FONTDIR/Hind-Regular.ttf'); }
@font-face { font-family: HindSB; src: url('FONTDIR/Hind-SemiBold.ttf'); }
@font-face { font-family: Kalam; src: url('FONTDIR/Kalam-Regular.ttf'); }
@font-face { font-family: Tiro; src: url('FONTDIR/TiroDevanagariHindi-Regular.ttf'); }
@font-face { font-family: Martel; src: url('FONTDIR/Martel-Regular.ttf'); }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { width: PAGEWpx; height: PAGEHpx; background: #fff; color: #111; font-family: BODYFONT; font-size: 25px; }
.page { width: 100%; height: 100%; padding: 80px 80px; position: relative; }
.nw { white-space: nowrap; }
h1 { font-family: HindSB; font-size: 34px; text-align: center; font-weight: normal; }
h2 { font-family: HindSB; font-size: 29px; text-align: center; font-weight: normal; margin-top: 8px; }
.sub { text-align: center; font-size: 21px; margin-top: 6px; color: #333; }
hr { border: 0; border-top: 2px solid #222; margin: 22px 0; }
.hw { font-family: Kalam; color: #1b2f8f; font-size: 30px; }
.stamp { position: absolute; border: 4px double #7a1f2b; color: #7a1f2b; border-radius: 50%; width: 210px; height: 210px;
         display: flex; align-items: center; justify-content: center; text-align: center; font-size: 20px; opacity: .55;
         transform: rotate(-14deg); }
.sign { position: absolute; bottom: 110px; right: 90px; text-align: center; font-size: 21px; }
.foot { position: absolute; bottom: 60px; left: 80px; right: 80px; font-size: 18px; color: #444; }
"""


def num(s: str, dev: bool) -> str:
    return s.translate(DEV_DIGITS) if dev else s


def v(field_name: str, text: str, hw: bool = False) -> str:
    cls = "hw nw" if hw else "nw"
    return f'<span class="{cls}" data-field="{field_name}">{text}</span>'


def tpl_khatauni_table(r: Record, rng: random.Random, dev_digits: bool, hw: bool) -> str:
    s, d, t = r.state, r.district, r.tehsil
    unit_hi = UNIT_TEXT[r.area_unit][0]
    head = "".join(f'<th class="nw">{h}</th>' for h in [
        "खसरा संख्या", f"क्षेत्रफल ({unit_hi})", "भूमि का प्रकार"])
    rows = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in [
        v("khasra_number", num(p["khasra"][0], dev_digits), hw),
        v("plot_area", num(f"{p['area_value']}", dev_digits), hw),
        v("land_classification", LAND_CLASS_TEXT[p["land_class"]][0], hw),
    ]) + "</tr>" for p in r.parcels)
    khata_block = f'<div class="row"><span class="nw">खाता संख्या :</span> {v("khata_number", num(r.khata, dev_digits), hw)}</div>'
    owner_names = " एवं ".join(v("owner_name", o[0], hw) for o, _ in r.owners)
    owner_block = f'<div class="row"><span class="nw">खातेदार का नाम :</span> {owner_names}</div>'
    fathers = [f for _, f in r.owners if f]
    if fathers:
        father_names = " एवं ".join(v("father_name", f[0], hw) for f in fathers)
        owner_block += f'<div class="row"><span class="nw">पिता / पति का नाम :</span> {father_names}</div>'
    survey = f'<div class="row"><span class="nw">सर्वे संख्या :</span> {v("survey_number", num(r.survey, dev_digits), hw)}</div>' if r.survey else ""
    mut = ""
    if r.mutation_no:
        mut = (f'<div class="row"><span class="nw">नामांतरण संख्या :</span> {v("mutation_number", num(r.mutation_no, dev_digits), hw)}'
               f'&nbsp;&nbsp;&nbsp;&nbsp;<span class="nw">नामांतरण दिनांक :</span> {v("mutation_date", num(r.mutation_date, dev_digits), hw)}</div>')
    reg = ""
    if r.reg_no:
        reg = (f'<div class="row"><span class="nw">पंजीकरण संख्या :</span> {v("registration_number", num(r.reg_no, dev_digits), hw)}'
               f'&nbsp;&nbsp;&nbsp;&nbsp;<span class="nw">पंजीकरण दिनांक :</span> {v("registration_date", num(r.reg_date, dev_digits), hw)}</div>')
    return f"""
<div class="page">
  <h1>{s['hi']} सरकार</h1>
  <h2>{s['record_title_hi']} (अधिकार अभिलेख)</h2>
  <div class="sub nw">फसली वर्ष {num(r.extras['fasli'], dev_digits)} &nbsp;|&nbsp; भाग - 1</div>
  <hr/>
  <div class="meta">
    <div class="row"><span class="nw">ग्राम :</span> {v("village", r.village[1], hw)}&nbsp;&nbsp;&nbsp;&nbsp;<span class="nw">तहसील :</span> {v("tehsil", t['hi'], hw)}</div>
    <div class="row"><span class="nw">जिला :</span> {v("district", d['hi'], hw)}&nbsp;&nbsp;&nbsp;&nbsp;<span class="nw">राज्य :</span> {v("state", s['hi'], hw)}</div>
  </div>
  <hr/>
  {khata_block}
  {owner_block}
  {survey}
  <table><tr>{head}</tr>{rows}</table>
  {mut}
  {reg}
  <div class="row small nw">टिप्पणी : प्रविष्टि क्रमांक {num(str(r.extras['remark_no']), dev_digits)} के अनुसार अंकित।</div>
  <div class="stamp" style="top:{rng.randint(1150, 1300)}px; left:{rng.randint(120, 380)}px;">राजस्व विभाग<br/>{d['hi']}</div>
  <div class="sign">हस्ताक्षर<br/>राजस्व निरीक्षक / लेखपाल</div>
  <div class="foot nw">यह प्रति भूलेख अभिलेख से ली गई है। केवल सूचनार्थ।</div>
</div>
<style>
 .row {{ margin: 14px 0; }} .meta .row {{ margin: 10px 0; }} .small {{ font-size: 21px; margin-top: 26px; }}
 table {{ border-collapse: collapse; width: 100%; margin: 26px 0; }}
 th, td {{ border: 2px solid #222; padding: 12px 10px; text-align: center; font-weight: normal; }}
 th {{ font-family: HindSB; font-size: 23px; }}
</style>"""


def tpl_form_bilingual(r: Record, rng: random.Random, dev_digits: bool, hw: bool) -> str:
    s, d, t = r.state, r.district, r.tehsil
    unit_hi = UNIT_TEXT[r.area_unit][0]
    lines = [
        ("राज्य / State", "state", s["hi"]),
        ("जिला / District", "district", d["hi"]),
        ("तहसील / Tehsil", "tehsil", t["hi"]),
        ("ग्राम / Village", "village", r.village[1]),
        ("खातेदार का नाम / Owner", "owner_name", r.owner[0]),
    ]
    if r.father:
        lines.append(("पिता का नाम / Father", "father_name", r.father[0]))
    lines += [
        ("खाता संख्या / Khata No.", "khata_number", num(r.khata, dev_digits)),
        ("खसरा संख्या / Khasra No.", "khasra_number", num(r.khasra[0], dev_digits)),
    ]
    if r.survey:
        lines.append(("सर्वे संख्या / Survey No.", "survey_number", num(r.survey, dev_digits)))
    lines += [
        ("क्षेत्रफल / Area", "plot_area", f"{num(str(r.area_value), dev_digits)} {unit_hi}"),
        ("भूमि का प्रकार / Land Class", "land_classification", LAND_CLASS_TEXT[r.land_class][0]),
    ]
    if r.mutation_no:
        lines += [("नामांतरण संख्या / Mutation No.", "mutation_number", num(r.mutation_no, dev_digits)),
                  ("नामांतरण दिनांक / Mutation Date", "mutation_date", num(r.mutation_date, dev_digits))]
    if r.reg_no:
        lines += [("पंजीकरण संख्या / Registration No.", "registration_number", num(r.reg_no, dev_digits)),
                  ("पंजीकरण दिनांक / Registration Date", "registration_date", num(r.reg_date, dev_digits))]
    body = "".join(
        f'<div class="fl"><span class="lb nw">{lb}</span><span class="colon">:</span><span class="val">{v(f, val, hw)}</span></div>'
        for lb, f, val in lines)
    return f"""
<div class="page">
  <h1>भूमि अभिलेख विवरण प्रपत्र</h1>
  <h2 class="nw">Land Record Particulars Form</h2>
  <div class="sub nw">{s['record_title_hi']} / {s['record_title_en']} &nbsp;&nbsp; क्रमांक {num(str(rng.randint(1000, 9999)), dev_digits)}</div>
  <hr/>
  {body}
  <div class="stamp" style="top:{rng.randint(1250, 1380)}px; left:{rng.randint(120, 420)}px;">तहसील कार्यालय<br/>{t['hi']}</div>
  <div class="sign">हस्ताक्षर / Signature<br/>पटवारी / Patwari</div>
</div>
<style>
 .fl {{ display: flex; align-items: center; margin: 15px 0; border-bottom: 1px dotted #999; padding-bottom: 5px; }}
 .lb {{ width: 480px; }} .colon {{ width: 30px; }} .val {{ flex: 1; }}
</style>"""


def tpl_ror_english(r: Record, rng: random.Random, dev_digits: bool, hw: bool) -> str:
    s, d, t = r.state, r.district, r.tehsil
    unit_en = UNIT_TEXT[r.area_unit][1]
    rows = [
        ("Name of Landowner", "owner_name", r.owner[1]),
    ]
    if r.father:
        rows.append(("Father's Name", "father_name", r.father[1]))
    rows += [("Khata No.", "khata_number", r.khata), ("Khasra No.", "khasra_number", r.khasra[1])]
    if r.survey:
        rows.append(("Survey No.", "survey_number", r.survey))
    rows += [("Area", "plot_area", f"{r.area_value} {unit_en}"),
             ("Land Classification", "land_classification", LAND_CLASS_TEXT[r.land_class][1])]
    if r.mutation_no:
        rows += [("Mutation No.", "mutation_number", r.mutation_no), ("Mutation Date", "mutation_date", r.mutation_date)]
    if r.reg_no:
        rows += [("Registration No.", "registration_number", r.reg_no), ("Registration Date", "registration_date", r.reg_date)]
    body = "".join(f'<tr><td class="nw lb">{lb}</td><td class="c">:</td><td>{v(f, val, hw)}</td></tr>' for lb, f, val in rows)
    return f"""
<div class="page">
  <h1 class="nw">GOVERNMENT OF {s['en'].upper()}</h1>
  <h2 class="nw">RECORD OF RIGHTS - EXTRACT ({s['record_title_en']})</h2>
  <div class="sub nw">Revenue Department &nbsp;|&nbsp; Serial No. {rng.randint(10000, 99999)}</div>
  <hr/>
  <div class="row nw">Village : {v("village", r.village[0], hw)} &nbsp;&nbsp;&nbsp; Tehsil : {v("tehsil", t['en'], hw)}</div>
  <div class="row nw">District : {v("district", d['en'], hw)} &nbsp;&nbsp;&nbsp; State : {v("state", s['en'], hw)}</div>
  <hr/>
  <table>{body}</table>
  <div class="row small nw">Certified that this extract is a true copy of the record maintained in this office.</div>
  <div class="stamp" style="top:{rng.randint(1250, 1380)}px; left:{rng.randint(120, 420)}px;">TEHSILDAR<br/>{t['en'].upper()}</div>
  <div class="sign">Signature<br/>Tehsildar / Revenue Officer</div>
</div>
<style>
 .row {{ margin: 12px 0; }} .small {{ font-size: 20px; margin-top: 30px; }}
 table {{ border-collapse: collapse; margin-top: 10px; }}
 td {{ padding: 10px 8px; vertical-align: baseline; }} .lb {{ width: 360px; }} .c {{ width: 30px; }}
</style>"""


TEMPLATES = {
    "khatauni_table": (tpl_khatauni_table, "hi", "Hind"),
    "form_bilingual": (tpl_form_bilingual, "hi", "Hind"),
    "ror_english": (tpl_ror_english, "en", "Martel"),
}

# JS: group visible text nodes into lines, and collect field boxes
EXTRACT_JS = """
() => {
  const items = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    const txt = n.textContent.replace(/\\s+/g, ' ').trim();
    if (!txt) continue;
    const el = n.parentElement;
    if (el.closest('style')) continue;
    const range = document.createRange(); range.selectNodeContents(n);
    for (const r of range.getClientRects()) {
      if (r.width < 1 || r.height < 1) continue;
      items.push({text: txt, x0: r.left, y0: r.top, x1: r.right, y1: r.bottom,
                  stamp: !!el.closest('.stamp')});
    }
  }
  const fields = {};
  document.querySelectorAll('[data-field]').forEach(el => {
    const r = el.getBoundingClientRect();
    (fields[el.dataset.field] = fields[el.dataset.field] || []).push([r.left, r.top, r.right, r.bottom]);
  });
  return {items, fields};
}
"""


def group_lines(items: list[dict]) -> list[dict]:
    items = sorted((i for i in items if not i["stamp"]), key=lambda i: (i["y0"] + i["y1"]) / 2)
    lines: list[list[dict]] = []
    for it in items:
        cy = (it["y0"] + it["y1"]) / 2
        for ln in lines:
            ly0 = min(i["y0"] for i in ln)
            ly1 = max(i["y1"] for i in ln)
            if ly0 <= cy <= ly1:
                ln.append(it)
                break
        else:
            lines.append([it])
    out = []
    for ln in lines:
        ln.sort(key=lambda i: i["x0"])
        out.append({"text": " ".join(i["text"] for i in ln),
                    "bbox": [min(i["x0"] for i in ln), min(i["y0"] for i in ln),
                             max(i["x1"] for i in ln), max(i["y1"] for i in ln)]})
    return out


# ---------------------------------------------------------------- degradation

PROFILES = ["clean", "scan", "scan", "old", "photo"]


def degrade(img: np.ndarray, profile: str, rng: random.Random) -> tuple[np.ndarray, np.ndarray, dict]:
    """Returns degraded image, 3x3 geometric transform, and params used."""
    h, w = img.shape[:2]
    nrng = np.random.default_rng(rng.randint(0, 2**31))
    params: dict = {"profile": profile}
    out = img.astype(np.float32)

    # paper tint
    tint = np.array([rng.uniform(200, 235), rng.uniform(222, 245), rng.uniform(232, 250)], np.float32)  # BGR
    if profile != "clean":
        out = out / 255.0 * tint
    # fading (old ink)
    if profile in ("old", "scan"):
        fade = rng.uniform(0.55, 0.8) if profile == "old" else rng.uniform(0.8, 0.95)
        out = 255 - (255 - out) * fade
        params["fade"] = round(fade, 2)
    # stains
    if profile == "old":
        for _ in range(rng.randint(2, 5)):
            mask = np.zeros((h, w), np.float32)
            cv2.ellipse(mask, (rng.randint(0, w), rng.randint(0, h)), (rng.randint(40, 180), rng.randint(30, 140)),
                        rng.uniform(0, 180), 0, 360, 1.0, -1)
            mask = cv2.GaussianBlur(mask, (0, 0), 25)[..., None]
            out = out * (1 - 0.25 * mask) + np.array([90, 140, 170], np.float32) * 0.25 * mask
    # geometry
    angle = rng.uniform(-1, 1) if profile == "clean" else rng.uniform(-4.5, 4.5)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    M3 = np.vstack([M, [0, 0, 1]])
    if profile == "photo":
        d = 0.04
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst = np.float32([[rng.uniform(0, d) * w, rng.uniform(0, d) * h], [w - rng.uniform(0, d) * w, rng.uniform(0, d) * h],
                          [w - rng.uniform(0, d) * w, h - rng.uniform(0, d) * h], [rng.uniform(0, d) * w, h - rng.uniform(0, d) * h]])
        M3 = cv2.getPerspectiveTransform(src, dst) @ M3
    border = tuple(float(x) for x in (tint if profile != "clean" else (255, 255, 255)))
    out = cv2.warpPerspective(out, M3, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=border)
    params["angle"] = round(angle, 2)
    # uneven lighting for photos
    if profile == "photo":
        gx = np.linspace(rng.uniform(0.7, 1.0), rng.uniform(0.9, 1.1), w, dtype=np.float32)
        gy = np.linspace(rng.uniform(0.8, 1.05), rng.uniform(0.75, 1.0), h, dtype=np.float32)
        out = out * (gy[:, None] * gx[None, :])[..., None]
    # blur + noise
    if profile != "clean":
        k = rng.choice([0, 1.0, 1.4]) if profile != "photo" else rng.choice([1.2, 1.8])
        if k:
            out = cv2.GaussianBlur(out, (0, 0), k)
        sigma = rng.uniform(3, 12)
        out = out + nrng.normal(0, sigma, out.shape).astype(np.float32)
        params["noise"] = round(sigma, 1)
    out = np.clip(out, 0, 255).astype(np.uint8)
    # jpeg artefacts
    if profile != "clean":
        q = rng.randint(35, 80)
        _, enc = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, q])
        out = cv2.imdecode(enc, cv2.IMREAD_COLOR)
        params["jpeg_q"] = q
    return out, M3, params


def warp_box(b: list[float], M3: np.ndarray) -> list[int]:
    pts = np.float32([[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]).reshape(-1, 1, 2)
    p = cv2.perspectiveTransform(pts, M3).reshape(-1, 2)
    return [int(p[:, 0].min()), int(p[:, 1].min()), int(math.ceil(p[:, 0].max())), int(math.ceil(p[:, 1].max()))]


# ---------------------------------------------------------------- main

def launch(p):
    for channel in ("msedge", "chrome", None):
        try:
            return p.chromium.launch(channel=channel) if channel else p.chromium.launch()
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError("No Chromium browser found. Install Edge/Chrome or run `playwright install chromium`.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=40)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--pdf-ratio", type=float, default=0.15, help="fraction of docs also saved as scanned PDF")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    ensure_fonts()
    gaz = json.loads(GAZETTEER.read_text(encoding="utf-8"))
    rng = random.Random(args.seed)
    out_dir = OUT_DIR / args.split
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_html = out_dir / "_render.html"
    font_url = FONT_DIR.resolve().as_uri()

    with sync_playwright() as p:
        browser = launch(p)
        page = browser.new_page(viewport={"width": PAGE_W, "height": PAGE_H}, device_scale_factor=1)
        for i in range(args.count):
            doc_id = f"{args.split}-{i + 1:03d}"
            tname = rng.choice(list(TEMPLATES))
            fn, script, font = TEMPLATES[tname]
            rec = make_record(rng, gaz, multi=tname == "khatauni_table")
            hw = tname == "form_bilingual" and rng.random() < 0.6 or tname == "khatauni_table" and rng.random() < 0.2
            dev_digits = script == "hi" and rng.random() < 0.25
            profile = rng.choice(PROFILES)

            css = (BASE_CSS.replace("FONTDIR", font_url).replace("PAGEW", str(PAGE_W))
                   .replace("PAGEH", str(PAGE_H)).replace("BODYFONT", font))
            html = f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{fn(rec, rng, dev_digits, hw)}</body></html>"
            tmp_html.write_text(html, encoding="utf-8")
            page.goto(tmp_html.resolve().as_uri())
            page.evaluate("document.fonts.ready")
            info = page.evaluate(EXTRACT_JS)
            png = page.screenshot(full_page=False)
            img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)

            deg, M3, params = degrade(img, profile, rng)
            cv2.imwrite(str(out_dir / f"{doc_id}.png"), deg)
            files = [f"{doc_id}.png"]
            if rng.random() < args.pdf_ratio:
                import fitz  # pymupdf

                pdf = fitz.open()
                pg = pdf.new_page(width=595, height=842)
                ok, enc = cv2.imencode(".jpg", deg, [cv2.IMWRITE_JPEG_QUALITY, 85])
                pg.insert_image(pg.rect, stream=enc.tobytes())
                pdf.save(out_dir / f"{doc_id}.pdf")
                files.append(f"{doc_id}.pdf")

            lines = group_lines(info["items"])
            meta = {
                "id": doc_id, "files": files, "template": tname, "script": script, "handwritten": hw,
                "devanagari_digits": dev_digits, "degradation": params,
                "fields": ground_truth(rec, script),
                "field_boxes": {k: [warp_box(b, M3) for b in boxes] for k, boxes in info["fields"].items()},
                "text_lines": [{"text": ln["text"], "bbox": warp_box(ln["bbox"], M3)} for ln in lines],
                "text": "\n".join(ln["text"] for ln in lines),
            }
            (out_dir / f"{doc_id}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{doc_id}  {tname:15s} {profile:6s} hw={hw!s:5s} dev={dev_digits!s:5s} {rec.district['en']}")
        browser.close()
    tmp_html.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
