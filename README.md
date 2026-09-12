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

Measured on 40 **held-out** synthetic documents (`test` split) whose places come from the official LGD village directory. The confidence model and threshold (95% target precision) were fitted on a separate `dev` split; the threshold sits in the middle of the range that meets that target, not at its lowest edge, because the lowest edge met it on dev and missed it on test. Reproduce with `python eval/evaluate.py --split test`; the full table is in [eval/results/test.md](eval/results/test.md).

| Metric | Held-out test | Dev (tuning split) |
| --- | --- | --- |
| Field accuracy (all 15 fields) | **88.1%** | 87.6% |
| Required-field accuracy | 87.5% | 87.5% |
| Character error rate, median / mean | 10.9% / 14.2% | 12.1% / 15.2% |
| Fields flagged for a human | **15.3%** | 21.3% |
| Precision of fields *not* flagged | **96.4%** | 96.4% |
| Auto-accepted documents with every required field correct | **11 of 13** | 10 of 10 |
| Documents needing a human look | 67.5% | 75.0% |

By document type (test): English Record of Rights 96.2%, clean pages 98.2%, old faded paper 95.3%, scanner-quality pages 89.5%, Khatauni tables 84.5%, handwritten entries 77.4%, **phone photos 56.5%** (still the weakest case). A page that reads badly is read a second time with lighter denoising, and numbers that read unsurely are read once more by a recogniser that knows English digits only — between them, most of the recent gain on photos, faded paper and the numbers a record is looked up by. When even the second read is poor, the quality check tells the operator to retake rather than guess.

Two things to read from this. First, the verifier checks about 1 field in 7 rather than retyping the page, and the fields left unflagged are right about 96% of the time. A third of documents now pass with no human at all. Second, the test split is the honest number: the label rules were tuned by looking at dev errors, and test was run once for this report (it came out slightly easier than dev, with fewer multi-owner Khataunis). OCR changes are A/B-tested before adoption; the ones that didn't help are written up in [eval/results/experiments.md](eval/results/experiments.md).

**Multi-owner Khataunis** (separate 30-document split on official LGD villages, with 1–3 co-owners and 1–4 parcel rows per khata; [eval/results/multi.md](eval/results/multi.md)): field accuracy 84.2%; every co-owner found on 3 of 6 multi-owner documents (6 of 9 on the test split), 16 of 23 parcel rows in multi-row tables recovered. The second read lifted this split by 2.3 points overall, though one document lost its exact co-owner match — that measure is all-or-nothing over six documents. OCR often reads the connector एवं ("and") as `एव` or `एच`; the splitter accepts both, while a real name initial like `एच.` is left alone.

The documents are deliberately hard: about 60% are degraded (faded/stained paper, scanner noise and skew, phone photos with perspective and uneven light), and some have handwritten entries or Devanagari digits. CER counts every character on the page, including stamps and footers, so it's a pessimistic number.

## Screens

Every screen works in Hindi and English (one click in the sidebar): labels, review reasons, photo advice, the audit trail and dates. The printed extract and the public QR check are always bilingual.

| | |
| --- | --- |
| ![Sign-in with one-click demo accounts](docs/screenshots/1-sign-in.jpg) | ![Review: the scan with a box on every field, next to the extracted values](docs/screenshots/2-review.jpg) |
| **Sign-in**: how it works in three steps, one-click demo accounts, Hindi / English switch | **Review**: boxes coloured by confidence on the cleaned scan; confirm, correct or reject with the keyboard |
| ![Dashboard](docs/screenshots/3-dashboard.jpg) | ![Records and GIS](docs/screenshots/4-records-gis.jpg) |
| **Dashboard**: what waits for a person, accuracy, state/district progress | **Records & GIS**: LRMS format, co-owners, parcel map, DILRMP report, CSV download |
| ![Verified extract with QR code](docs/screenshots/5-verified-extract.jpg) | ![Public check on a phone](docs/screenshots/6-public-check-phone.jpg) |
| **Verified extract**: printable and bilingual, with a tamper-evident fingerprint and QR code | **Public check**: anyone scanning the QR sees, in English and Hindi, whether the paper still matches the record |

**हिंदी में (in Hindi)**: the same review screen after one click on the language switch.

![Review screen in Hindi](docs/screenshots/7-review-hindi.jpg)

## What maps to the problem statement

| PS 26018 asks for | In LandLekha |
| --- | --- |
| Multilingual recognition | Hindi (Devanagari) + English, in one model; Devanagari digits; bilingual labels |
| Extraction from scans, PDFs, images | PNG/JPG/TIFF/PDF upload, phone camera capture, multi-page PDFs. Born-digital PDFs are read from their text layer (0.5 s, exact). Pages photographed sideways or upside down are turned automatically (18/18 test pages recovered). Each page gets a quality verdict with retake advice, and a page that reads badly is read again with lighter denoising (+2.2 points of field accuracy on dev) |
| Classification into predefined fields | 15 fields (`backend/extraction/schema.py`), found in key:value forms, filled forms and Khatauni tables; every co-owner and parcel row under a khata (`owners` / `parcels` lists) |
| Validation: business rules, cross-database, duplicates | Format rules per field, master gazetteer (state → district → tehsil → village) with hierarchy checks, duplicate detection on parcel/account + exact-file hash |
| Confidence scoring, uncertain fields flagged | Logistic calibration over OCR, rule, label and source evidence; per-field threshold |
| Human-assisted verification | Side-by-side review screen, confirm / correct / reject per field; the queue shows how many fields each document needs checked and can be ordered lowest-confidence or fewest-fields first; unsaved corrections survive a reload |
| Learning that improves over time | Verifier corrections are remembered and re-applied; fields that are corrected often get stricter thresholds |
| LRMS / DILRMP / GIS / cadastral integration | Documented REST + GraphQL (`/api/graphql`) endpoints: LRMS exchange format + push, DILRMP progress report, GeoJSON parcels on a Leaflet map (external systems simulated) |
| Secure repository, metadata, audit trail | Stored originals + SHA-256, per-document metadata, append-only audit log of every action, filterable by person or kind of event and downloadable as a spreadsheet for the compliance file; login rate-limiting against brute force |
| Dashboards | Processed count, auto-accept rate, accuracy, validation status, pending cases, error statistics, state/district progress; each status opens the documents behind it, and any filtered list downloads as a spreadsheet; CSV export (`/api/admin/export/*.csv`) for external BI tools |
| Notifications | Pluggable service (email/webhook) notifies an operator when their document is reviewed or flagged; console-only until a real provider is configured |
| APIs | FastAPI with OpenAPI docs at `/docs`, plus GraphQL at `/api/graphql` |
| Role-based access | JWT; operator / verifier / admin enforced on every endpoint; failed logins are rate-limited per IP+username |
| Usability and accessibility | Every screen in Hindi and English, with a test that fails if any on-screen string lacks Hindi; axe audit with 0 violations on 11 screens; phone layouts (cards instead of wide tables) with thumb-sized controls |

## Run it

Requires Python 3.11+ and Node 18+.

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.api.main:app --port 8000        # API + docs at http://localhost:8000/docs

cd frontend && npm install && npm run dev                  # UI at http://localhost:5173
```

The first start downloads the EasyOCR models (about 100 MB). For a single-port demo, run `npm run build` in `frontend/`; the API then serves the UI at http://localhost:8000.

Or start everything with one command: `scripts\start.ps1` on Windows (`powershell -ExecutionPolicy Bypass -File scripts\start.ps1`), or `scripts/start.sh` elsewhere. Add `-Fresh` / `--fresh` for an empty database before a demo, and `-Built` / `--built` to serve the built UI from port 8000.

Keep the project **outside** a OneDrive/Dropbox-synced folder if you can. Sync clients re-upload every generated image and OCR cache file and can make processing several times slower.

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
python data/generator/generate.py --count 30 --split multi --seed 5   # multi-owner Khatauni results
python eval/evaluate.py --split dev        # runs OCR once, caches it, measures
python eval/calibrate.py --split dev       # fits confidence model + threshold
python eval/evaluate.py --split test       # report on held-out data
python -m pytest tests -q                  # fast extraction tests (no OCR)
python scripts/a11y_check.py               # axe accessibility audit of every screen, both languages (app running)
cd frontend && npm test                    # frontend unit tests; also fails if any on-screen string lacks Hindi
```

`data/demo/` has six small committed files for the live demo, with expected answers in `data/demo/expected.md`. The script is [docs/demo-script.md](docs/demo-script.md).

## Honest scope

- **Data is synthetic.** The pipeline has not yet been measured on real registers. Getting a few hundred real, redacted records is step one after selection.
- **Handwriting** means legible handwritten entries in forms. Cursive registers need fine-tuning on real Indic handwriting (e.g. with TrOCR or Indic OCR models).
- **External systems are simulated.** The LRMS/DILRMP/GIS APIs are real and documented (REST and now [GraphQL](backend/api/graphql_api.py)), but pushes return a mock acknowledgement and parcel geometry is synthetic (placed near the district HQ and sized by area). Wiring in a real government endpoint is a matter of pointing `lrms_push` at it — no real endpoint exists to test against yet.
- **Master data** covers 4 states and 10 districts. Village English names and LGD codes are real, from the Ministry of Panchayati Raj's Local Government Directory. Village **Hindi spellings are algorithmically transliterated and not verified** against official local-script spelling — a native-speaker review is step one before trusting them in production (see `backend/extraction/master/gazetteer.json`'s `_note` and `backend/extraction/transliterate.py`). Expanding this to more states requires downloading real LGD data per state — synthesizing plausible-looking village codes would silently corrupt real land records, so this hasn't been faked.
- **The name lexicon** (`backend/extraction/master/name_tokens.json`) restores diacritics the OCR drops (सिह → सिंह). It overlaps with the generator's name lists, so name accuracy on synthetic data is somewhat optimistic.
- **Speed:** scanned pages take ~12 s on this machine's CPU (16 logical cores), above the 10 s target but down from 18.7 s after torch was told to use every core instead of its default half (`backend/ocr/engine.py`) - identical output, ~35% faster, measured on the `multi` eval split. Most of the remaining time is the neural OCR. Born-digital PDFs take 0.5 s. A CUDA GPU brings scanned pages to about 1–2 s. A smaller detection canvas was tested and rejected: it lost accuracy with no real speed-up. Machines with fewer cores will see a smaller gain from the threading fix and stay further from the 10 s target.
- **Phone photos:** a pre-OCR check now rejects catastrophically blurred/low-res photos in milliseconds instead of after a full OCR pass, and glare/reflection is now detected and flagged (`backend/ocr/quality.py`). The underlying accuracy problem on phone photos (71.9% word-level, per `eval/results/experiments.md`) is a recognition-model limitation that needs fine-tuning on real field photos - a UX/speed fix, not an accuracy fix.
- **Scaling:** each process runs one worker thread, but the queue is now database-backed (`backend/api/processing.py`), so multiple API replicas can share one Postgres database and safely split the load — see the scaling note in `docker-compose.yml`. The default SQLite mode stays single-process.
- **Notifications, GraphQL, BI export, login throttling:** a pluggable notification service (`backend/api/notifications.py`, console-only until `LL_SMTP_HOST`/`LL_NOTIFY_WEBHOOK_URL` is set), a GraphQL endpoint at `/api/graphql` alongside REST, CSV exports at `/api/admin/export/*.csv` for BI tools (Power BI/Superset/Grafana all read CSV/HTTP), and login rate-limiting (`backend/api/ratelimit.py`) have been added. These close real gaps but the ones needing external accounts (an actual SMS/email provider, a live LRMS endpoint, a hosted BI dashboard) are scaffolded, not connected — there is nothing real to connect to yet.

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
