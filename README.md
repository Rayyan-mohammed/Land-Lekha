# LandLekha

AI-powered land record digitization and validation system — SIH 2026, PS 26018 (DoLR, Ministry of Rural Development).

Scanned or photographed land records (printed or handwritten, Hindi + English) go in; structured, validated fields with a confidence score each come out. Confident records are accepted automatically, uncertain fields go to a human verifier.

## Repository layout

| Path | Track | What |
| --- | --- | --- |
| `backend/ocr/` | A — Vision/OCR | preprocessing (OpenCV) and OCR engine |
| `backend/extraction/` | B — NLP/Validation | field parser, validation, confidence, duplicates, master data |
| `backend/api/` | C — Backend | FastAPI app, DB, auth/RBAC, audit, mock integrations |
| `frontend/` | D — Frontend | React + Tailwind UI |
| `data/generator/` | shared | synthetic Hindi/English land record dataset with ground truth |
| `eval/` | shared | CER and field-accuracy evaluation |
| `docs/` | shared | data contracts between tracks |

## Dataset

No public labelled dataset of Indian land records exists, so we generate one: realistic Khatauni / Khasra / Jamabandi / Khatiyan style records for UP, MP, Rajasthan and Bihar, rendered with real Devanagari shaping and degraded to look like scans, old faded paper and phone photos. Some entries use a handwriting font and Devanagari digits.

```bash
pip install -r backend/requirements.txt
python data/generator/generate.py --count 40 --split dev --seed 1
python data/generator/generate.py --count 40 --split test --seed 2
```

Each document comes with a `.json` holding the exact field values, field boxes and full text (for CER).
