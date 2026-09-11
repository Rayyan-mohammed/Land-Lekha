# LandLekha

**AI-powered land record digitization and validation.** SIH 2026 · PS 26018 · Department of Land Resources, Ministry of Rural Development.

LandLekha takes a scanned or photographed land record (printed or handwritten, Hindi or English) and turns it into structured, validated data: owner, khata, khasra, survey number, area, land class, village, tehsil, district, mutation and registration details. Every field gets a calibrated confidence score. Confident records are accepted automatically; uncertain fields go to a verifier, who sees the scan and the machine's answer side by side and only checks what is flagged.

```mermaid
flowchart LR
  U[Upload<br/>image / PDF / phone photo] --> P[Preprocess<br/>OpenCV: page crop, illumination,<br/>deskew, denoise, CLAHE]
  P --> O[OCR<br/>EasyOCR hi+en]
  O --> X[Extract<br/>fuzzy label spotting<br/>same line / beside / table cell]
  X --> V[Validate<br/>format rules, master gazetteer,<br/>hierarchy, duplicates]
  V --> C[Calibrated confidence<br/>per field]
  C -->|all fields above threshold| A[Auto-accept]
  C -->|anything uncertain| R[Verifier review]
  R -->|corrections| L[(Learning memory)]
  L --> X
  A --> DB[(Land records<br/>+ audit trail)]
  R --> DB
  DB --> API[REST APIs<br/>LRMS · DILRMP · GIS]
  DB --> D[Dashboards / MIS]
```

## Results

Measured on 40 **held-out** synthetic documents (`test` split). The confidence model and threshold were fitted on a separate `dev` split. Reproduce with `python eval/evaluate.py --split test`; the full table is in [eval/results/test.md](eval/results/test.md).

| Metric | Held-out test | Dev (tuning split) |
| --- | --- | --- |
| Field accuracy (all 15 fields) | **82.7%** | 89.0% |
| Required-field accuracy | 82.9% | 86.1% |
| Character error rate, median / mean | 11.3% / 16.7% | 11.8% / 16.5% |
| Fields flagged for a human | **17.7%** | 16.2% |
| Precision of fields *not* flagged | **96.4%** | 98.6% |
| Auto-accepted documents with every required field correct | **100%** (6 of 6) | 100% (10 of 10) |
| Documents needing a human look | 85% | 75% |

By document type (test): English Record of Rights 97.3%, scanner-quality pages 92.3%, clean pages 88.0%, old faded paper 83.7%, handwritten entries 75.4%, Khatauni tables 70.5%, **phone photos 58.6%** (the weakest case).

Two things to read from this. First, the verifier checks about 1 field in 6 rather than retyping the page, and the fields left unflagged are right about 96% of the time. Second, the drop from dev to test is real: the label rules were tuned by looking at dev errors, so the test split is the honest number.

The documents are deliberately hard: about 60% are degraded (faded/stained paper, scanner noise and skew, phone photos with perspective and uneven light), and some have handwritten entries or Devanagari digits. CER counts every character on the page, including stamps and footers, so it's a pessimistic number.

## What maps to the problem statement

| PS 26018 asks for | In LandLekha |
| --- | --- |
| Multilingual recognition | Hindi (Devanagari) + English, in one model; Devanagari digits; bilingual labels |
| Extraction from scans, PDFs, images | PNG/JPG/TIFF/PDF upload, phone camera capture, multi-page PDFs |
| Classification into predefined fields | 15 fields (`backend/extraction/schema.py`), found in key:value forms, filled forms and Khatauni tables |
| Validation: business rules, cross-database, duplicates | Format rules per field, master gazetteer (state → district → tehsil → village) with hierarchy checks, duplicate detection on parcel/account + exact-file hash |
| Confidence scoring, uncertain fields flagged | Logistic calibration over OCR, rule, label and source evidence; per-field threshold |
| Human-assisted verification | Side-by-side review screen, confirm / correct / reject per field, lowest-confidence-first queue |
| Learning that improves over time | Verifier corrections are remembered and re-applied; fields that are corrected often get stricter thresholds |
| LRMS / DILRMP / GIS / cadastral integration | Documented REST endpoints: LRMS exchange format + push, DILRMP progress report, GeoJSON parcels on a Leaflet map (external systems simulated) |
| Secure repository, metadata, audit trail | Stored originals + SHA-256, per-document metadata, append-only audit log of every action |
| Dashboards | Processed count, auto-accept rate, accuracy, validation status, pending cases, error statistics, state/district progress |
| APIs | FastAPI with OpenAPI docs at `/docs` |
| Role-based access | JWT; operator / verifier / admin enforced on every endpoint |

## Run it

Requires Python 3.11+ and Node 18+.

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.api.main:app --port 8000        # API + docs at http://localhost:8000/docs

cd frontend && npm install && npm run dev                  # UI at http://localhost:5173
```

The first start downloads the EasyOCR models (about 100 MB). For a single-port demo, run `npm run build` in `frontend/`; the API then serves the UI at http://localhost:8000.

Demo accounts (created on first start; disable with `LL_SEED_DEMO_USERS=0`):

| User | Password | Can |
| --- | --- | --- |
| `operator` | `upload@123` | upload, see own documents |
| `verifier` | `verify@123` | + review queue, verify, push to LRMS, dashboard |
| `admin` | `admin@123` | + users, full audit trail, re-run processing |

Configuration is through environment variables or `.env`; see [.env.example](.env.example). SQLite is the default; set `LL_DATABASE_URL` for PostgreSQL.

## Dataset

There is no public labelled dataset of Indian land records, so `data/generator/` builds one. It renders Khatauni (UP), Khasra Panchsala (MP), Jamabandi (Rajasthan) and Khatiyan (Bihar) style records in a real browser engine, so Devanagari shaping is correct. It uses three layouts: a table, a bilingual filled form and an English Record of Rights. Some records get a handwriting font in blue ink and Devanagari digits. Pages are then degraded to look like scans, old paper and phone photos. Every document comes with exact ground truth: field values, field boxes and full text.

```bash
python data/generator/generate.py --count 40 --split dev  --seed 1
python data/generator/generate.py --count 40 --split test --seed 2
python eval/evaluate.py --split dev        # runs OCR once, caches it, measures
python eval/calibrate.py --split dev       # fits confidence model + threshold
python eval/evaluate.py --split test       # report on held-out data
python -m pytest tests -q                  # fast extraction tests (no OCR)
```

`data/demo/` has six small committed files for the live demo, with expected answers in `data/demo/expected.md`. The script is [docs/demo-script.md](docs/demo-script.md).

## Honest scope

- **Data is synthetic.** The pipeline has not yet been measured on real registers. Getting a few hundred real, redacted records is step one after selection.
- **Handwriting** means legible handwritten entries in forms. Cursive registers need fine-tuning on real Indic handwriting (e.g. with TrOCR or Indic OCR models).
- **External systems are simulated.** The LRMS/DILRMP/GIS APIs are real and documented, but pushes return a mock acknowledgement and parcel geometry is synthetic (placed near the district HQ and sized by area).
- **Master data** covers 4 states, 10 districts and a sample of villages. Production would load the official LGD village directory.
- **The name lexicon** (`backend/extraction/master/name_tokens.json`) restores diacritics the OCR drops (सिह → सिंह). It overlaps with the generator's name lists, so name accuracy on synthetic data is somewhat optimistic.
- **Speed:** on this laptop's CPU (i7-13700H, no GPU) a page takes 11–24 s end to end, above the 10 s target. Most of that is the neural OCR. Levers already identified: a 1024 px detection canvas halves detection time with similar boxes (needs re-validation), and any CUDA GPU brings a page to about 1–2 s. Documents go through a single worker queue, so uploads never block the UI.

## Repository layout

| Path | Track | What |
| --- | --- | --- |
| `backend/ocr/` | A — Vision/OCR | preprocessing (OpenCV), OCR engine wrapper, pipeline |
| `backend/extraction/` | B — NLP/Validation | label spotting, parsers/validators, gazetteer, confidence, duplicates, learning |
| `backend/api/` | C — Backend | FastAPI app, models, auth/RBAC, audit, worker queue, integration APIs |
| `frontend/` | D — Frontend | React + Tailwind: upload, review, dashboard, records/GIS, audit, users |
| `data/generator/`, `data/demo/` | shared | synthetic dataset generator, demo set |
| `eval/` | shared | CER / field accuracy evaluation and confidence calibration |
| `docs/` | shared | [data contracts between tracks](docs/contracts.md), demo script |
| `tests/` | shared | extraction unit tests |
