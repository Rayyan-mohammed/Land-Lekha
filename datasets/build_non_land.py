"""Build the non-land half of the classification evaluation set, and OCR it the same way an
upload is OCR'd, so the classifier is measured on what it would actually see.

Everything here is synthetic and generic - no real person's document - across the kinds of
page an office actually receives by mistake: certificates, invoices, bank statements, a
newspaper, letters, a handwritten-style note, an unrelated government form, a product label,
a blank page, and a photograph with no text at all.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from backend.ocr.pipeline import run_ocr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "datasets" / "non_land"
random.seed(7)

FONTS = [r"C:/Windows/Fonts/arial.ttf", r"C:/Windows/Fonts/times.ttf", r"C:/Windows/Fonts/segoeui.ttf",
         r"C:/Windows/Fonts/cour.ttf", r"C:/Windows/Fonts/calibri.ttf"]
HAND = [r"C:/Windows/Fonts/segoepr.ttf", r"C:/Windows/Fonts/segoesc.ttf", r"C:/Windows/Fonts/comic.ttf"]
HINDI = [r"C:/Windows/Fonts/Nirmala.ttf", r"C:/Windows/Fonts/mangal.ttf"]


def font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def page(lines, kind, name, *, hand=False, hindi=False, tilt=0.0, stain=False, size=(1240, 1754)):
    img = Image.new("L", size, random.choice([255, 250, 243, 236]))
    d = ImageDraw.Draw(img)
    f = font(HAND if hand else HINDI if hindi else FONTS, random.choice([30, 34, 38]))
    y = 120
    for ln in lines:
        d.text((110 + random.randint(-6, 6), y), ln, fill=random.choice([0, 20, 40]), font=f)
        y += random.randint(54, 70)
    arr = np.array(img)
    if stain:
        yy, xx = np.mgrid[0:size[1], 0:size[0]]
        for _ in range(3):
            cy, cx, r = random.randint(200, size[1] - 200), random.randint(200, size[0] - 200), random.randint(80, 200)
            arr = np.where((yy - cy) ** 2 + (xx - cx) ** 2 < r * r, np.clip(arr.astype(int) - 45, 0, 255), arr).astype(np.uint8)
    if tilt:
        m = cv2.getRotationMatrix2D((size[0] / 2, size[1] / 2), tilt, 1.0)
        arr = cv2.warpAffine(arr, m, size, borderValue=255)
    folder = OUT / kind
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    cv2.imwrite(str(path), arr)
    return path


def photo(kind, name):
    """A photograph of something: colour gradient plus blobs, no writing on it."""
    h, w = 1200, 1600
    yy, xx = np.mgrid[0:h, 0:w]
    img = np.zeros((h, w, 3), np.uint8)
    img[..., 0] = (xx / w * 180 + 40).astype(np.uint8)
    img[..., 1] = (yy / h * 160 + 60).astype(np.uint8)
    img[..., 2] = ((np.sin(xx / 90) + np.cos(yy / 70)) * 50 + 120).astype(np.uint8)
    for _ in range(12):
        cv2.circle(img, (random.randint(0, w), random.randint(0, h)), random.randint(40, 220),
                   tuple(int(v) for v in np.random.randint(0, 255, 3)), -1)
    img = cv2.GaussianBlur(img, (0, 0), 3)
    folder = OUT / kind
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    cv2.imwrite(str(path), img)
    return path


docs = [
    ("certificates", "school_certificate", ["CENTRAL BOARD OF SECONDARY EDUCATION", "Senior School Certificate Examination",
        "Roll No 4211873", "This is to certify that PRIYA VERMA", "has passed with Grade A1", "Mathematics 95  Physics 91",
        "Chemistry 89  English 88", "Controller of Examinations"], {}),
    ("certificates", "birth_certificate", ["GOVERNMENT OF KARNATAKA", "Department of Health and Family Welfare",
        "BIRTH CERTIFICATE", "This is to certify that the birth of", "Aarav Kumar, on 14 March 2015,", "has been registered",
        "Registration No 2015/BLR/44812", "Registrar of Births and Deaths"], {"tilt": 1.5}),
    ("invoices", "shop_invoice", ["TAX INVOICE", "Acme Traders Pvt Ltd", "GSTIN 07AABCU9603R1ZM", "Item  Qty  Rate  Amount",
        "Steel pipes  12  450.00  5400.00", "Cement bags  30  380.00  11400.00", "Total due Rs 16,800.00",
        "Payment terms 30 days"], {}),
    ("invoices", "hindi_bill", ["चालान / बीजक", "शर्मा जनरल स्टोर, लखनऊ", "बिल संख्या 4471", "चावल 25 किलो 1250", "दाल 10 किलो 900",
        "कुल राशि 2150 रुपये", "भुगतान नकद", "धन्यवाद"], {"hindi": True}),
    ("bank", "account_statement", ["STATE BANK  Account Statement", "Account No XXXX4471  IFSC SBIN0001234", "Branch code 01234",
        "Date  Description  Debit  Credit  Balance", "01/04  Opening balance  -  -  45,210.00", "03/04  UPI transfer  1,200.00  -  44,010.00",
        "09/04  Salary credit  -  52,000.00  96,010.00", "Closing balance 96,010.00"], {}),
    ("letters", "office_letter", ["Dear Sir,", "With reference to your letter dated 4 June,", "please find enclosed the minutes of",
        "the meeting held on Monday. Kindly", "confirm the dates for the next review.", "Thanking you,", "Yours faithfully,",
        "R. Menon, Office Superintendent"], {"tilt": -1.0}),
    ("handwritten_notes", "shopping_note", ["milk 2 packets", "bread", "call electrician about fan", "school fees before 10th",
        "pick up medicines", "sugar 1 kg, tea", "birthday gift for Anu"], {"hand": True, "stain": True, "tilt": 2.0}),
    ("handwritten_notes", "lecture_notes", ["Chapter 4 - Photosynthesis", "light reaction in thylakoid", "dark reaction - Calvin cycle",
        "6CO2 + 6H2O -> C6H12O6 + 6O2", "chlorophyll a and b", "revise before Friday test"], {"hand": True, "tilt": -2.5}),
    ("government_non_land", "vaccination_certificate", ["GOVERNMENT OF INDIA", "Ministry of Health and Family Welfare",
        "CERTIFICATE OF VACCINATION", "Name: Suresh Patil   Age: 42", "Vaccine: COVISHIELD  Dose 2", "Date: 12/08/2021",
        "Vaccinated at District Hospital, Pune", "Seal of the Medical Officer"], {}),
    ("government_non_land", "ration_card_form", ["GOVERNMENT OF UTTAR PRADESH", "Food and Civil Supplies Department",
        "APPLICATION FOR RATION CARD", "Applicant name  Father's name", "Address  District Lucknow", "Family members: 5",
        "Aadhaar linked: Yes", "Signature of applicant"], {"tilt": 0.8}),
    ("newspapers", "daily_page", ["THE DAILY HERALD  City Edition", "Council approves new bus routes", "Our correspondent reports that",
        "the new schedule begins Monday.", "Weather: rain expected through the weekend", "Sports: local club wins final 2-1",
        "Classifieds  Editorial  Letters"], {}),
    ("photographs", "product_label", ["FRESH MANGO JUICE", "Net volume 1 litre", "Ingredients: mango pulp, water, sugar",
        "Best before 6 months from packing", "MRP Rs 120  Batch 22A", "Store in a cool dry place"], {"tilt": 3.0}),
]

records = []
for kind, name, lines, kw in docs:
    path = page(lines, kind, name, **kw)
    records.append((kind, name, path))
records.append(("photographs", "street_photo", photo("photographs", "street_photo")))
blank = OUT / "photographs" / "blank_page.png"
cv2.imwrite(str(blank), np.full((1754, 1240), 248, np.uint8))
records.append(("photographs", "blank_page", blank))

for kind, name, path in records:
    out = path.with_suffix(".ocr.json")
    if out.exists():
        continue
    try:
        ocr = run_ocr(path.read_bytes(), path.name)
    except Exception as exc:  # a blank page may legitimately fail the quality precheck
        ocr = {"pages": [], "error": f"{type(exc).__name__}: {exc}"}
    out.write_text(json.dumps(ocr, ensure_ascii=False), encoding="utf-8")
    n = sum(len(p.get("tokens", [])) for p in ocr.get("pages", []))
    print(f"{kind:20} {name:24} tokens={n}", flush=True)
print("NONLAND DONE")
