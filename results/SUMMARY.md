# LandLekha — results for the PPT

Everything here is copied from `eval/results/*.md` (the actual measured output) — nothing is
invented. Charts are in `charts/`, real app screenshots are in `screenshots/`. Organized below
by suggested slide, so you can lift a slide's worth of content in one pass.

---

## Slide: "Architecture" → `charts/00_architecture.png`

The pipeline end to end, coloured by which track owns each part (matches README's mermaid diagram).

**Talking point**: the loop at the center is the point — an auto-accepted record and a verifier-approved one land in the same database indistinguishably, but every correction a verifier makes feeds back into the extraction step through the learning memory, so the system keeps improving without retraining.

---

## Headline numbers (put these on a "results at a glance" slide)

| Number | What it means |
| --- | --- |
| **88.1%** | Field accuracy across all 15 fields, on 40 held-out documents never seen during tuning |
| **96.4%** | Precision of the fields the system does NOT flag for review — i.e. when it doesn't ask a human to check, it's right 96.4% of the time |
| **15.3%** | Share of fields flagged for a human — the verifier checks about 1 field in 7, not the whole document |
| **100%** | Accuracy, precision and recall of the land-document classifier (105 land + 10 non-land pages, 115 real OCR readings) |
| **84.3% vs 10.4%** | Field accuracy on phone photos the quality gate accepted vs. the ones it sent back for a retake — the two groups never overlap |
| **6 states, 71 districts, 33,942 villages** | Real government village data (Ministry of Panchayati Raj LGD directory), not made up |
| **82 + 34** | Backend + frontend automated tests, all green in CI |
| **Live** | http://65.2.234.77:8000 — actually deployed, AWS EC2 + Docker + Postgres |

---

## Slide: "Overall accuracy" → `charts/01_overall_accuracy_by_split.png`

Three separate evaluation splits, so the number isn't cherry-picked from one lucky run:

| Split | Field accuracy | Required-field accuracy | Precision on unflagged fields | Documents |
| --- | --- | --- | --- | --- |
| Dev (used to tune the confidence threshold) | 87.6% | 87.5% | 96.4% | 40 |
| **Test (held-out — the honest number)** | **88.1%** | 87.5% | **96.4%** | 40 |
| Multi-owner (hardest split — several co-owners/parcels per khata) | 85.2% | 83.8% | 94.3% | 30 |

**Talking point**: test came out slightly *better* than dev, and the threshold was deliberately set to trade some auto-accept rate for a safety margin (see "How the threshold was chosen" below) — this isn't a number that got lucky on tuning data.

---

## Slide: "Which fields are hardest" → `charts/02_per_field_accuracy_test.png`

Per-field accuracy, test split (40 documents), sorted low to high:

| Field | Accuracy | Field | Accuracy |
| --- | --- | --- | --- |
| khasra_number | 77.5% | mutation_number | 88.6% |
| plot_area | 77.5% | khata_number | 87.5% |
| survey_number | 80.8% | registration_date | 87.0% |
| father_name | 83.3% | mutation_date | 85.7% |
| registration_number | 91.3% | owner_name | 90.0% |
| village | 90.0% | tehsil | 95.0% |
| district | 95.0% | state | 95.0% |
| land_classification | 95.0% | | |

**Talking point**: the weakest fields (khasra number, plot area) are exactly the ones with the most varied handwritten formats and OCR digit confusion — which is *why* the project built a second, English-only re-read pass specifically for numbers (see Roadmap/experiments below).

---

## Slide: "Accuracy by document condition" → `charts/03_accuracy_by_document_condition.png`

| Condition | Accuracy | Condition | Accuracy |
| --- | --- | --- | --- |
| Clean scan | 98.2% | Khatauni table | 84.5% |
| English Record of Rights | 96.2% | Bilingual form | 82.6% |
| Old/faded paper | 95.3% | Handwritten | 77.4% |
| Printed | 90.6% | **Phone photo** | **56.5%** |
| Scanner | 89.5% | | |

**Talking point**: this is the honest weak spot, stated plainly — phone photos are hard. The next chart shows what's actually done about it.

---

## Slide: "The phone-photo quality gate" → `charts/04_phone_photo_quality_gate.png`

Across all 17 phone photos in the three evaluation splits:

- **12 of 17** were accepted by a pre-OCR quality check → averaged **84.3%** field accuracy (worst case: 63.6%)
- **5 of 17** were rejected and sent back for a retake → averaged **10.4%** field accuracy (best case: 21.4%)
- **The two groups never overlap.** The worst photo it kept still beat the best photo it rejected.

**Talking point**: the system doesn't guess on a photo it can't read — it says so, at the counter, in Hindi or English, with advice ("hold steady", "avoid glare"), instead of quietly writing a wrong khasra number into the register.

---

## Slide: "Is this even a land record?" → `charts/05_classifier_confusion_matrix.png`

Before a single field is extracted, a rule ensemble decides whether the page is a land record at all:

- Measured on **115 real OCR readings**: 105 actual land pages + 10 deliberately-not-land pages (bills, letters, certificates, newspapers, photos)
- **105/105 land pages kept, 10/10 non-land pages refused, 0 mistakes**
- 100% accuracy, precision, recall, F1 = 1.000

**Talking point**: a bank statement or an electricity bill photographed by mistake never reaches the register with a fabricated khasra number. Honest caveat: the non-land test set is only 14 pages and synthetic — this proves the mechanism works, not that it's bulletproof against every kind of paper an office would see.

---

## Slide: "Human-in-the-loop, not human-does-everything" → `charts/06_document_routing.png`

Of 40 test documents:
- **13 (32%) auto-accepted** — no human touched them at all
- **27 (68%) sent to a verifier** — but only the flagged fields, not a full retype
- Of auto-accepted documents, **84.6%** were fully correct on every required field (straight-through accuracy)

**Talking point**: pair this with the 15.3%-fields-flagged number — a verifier isn't rereading each of the 27 documents field by field, they're checking an average of ~1-2 flagged fields per document.

---

## Slide: "Real Khataunis have multiple owners" → `charts/07_multiowner_parcel_recovery.png`

A khata can have several co-owners and several parcel (khasra) rows — most systems assume one owner, one plot. LandLekha models the real structure:

| Metric | Dev | Test | Multi-owner split (hardest) |
| --- | --- | --- | --- |
| Owner list exactly right | 82.5% | 85.0% | 76.7% |
| Every co-owner found | 9 of 13 | 6 of 9 | 3 of 6 |
| Parcel rows recovered (recall) | 62.2% | 62.9% | 55.6% |

**Talking point**: this is the hardest, most honestly-reported number in the whole project — the co-owner match is all-or-nothing per document over a small sample, so it swings a lot. Say that plainly if asked; it's more credible than hiding it.

---

## Slide: screenshots (use `screenshots/*.jpg` directly)

| File | Shows |
| --- | --- |
| `1-sign-in.jpg` | Sign-in, one-click demo accounts, Hindi/English switch |
| `2-review.jpg` | Review screen: confidence-coloured boxes on the scan next to extracted values |
| `3-dashboard.jpg` | Dashboard: accuracy, pending cases, state/district progress |
| `4-records-gis.jpg` | Records & GIS: LRMS format, co-owners, parcel map |
| `5-verified-extract.jpg` | Verified extract: bilingual, QR code, tamper-evident fingerprint |
| `6-public-check-phone.jpg` | Public QR check on a phone — no login needed |
| `7-review-hindi.jpg` | The same review screen in Hindi, one click away |

---

## Slide: "What makes this different" (USPs — pick 3-4 for time)

1. **It checks the page is a land record before trusting anything on it** — 100% on the classifier (above).
2. **Calibrated confidence, not raw OCR score** — raw OCR confidence for Devanagari is badly calibrated (correct text often scores only 0.4–0.6); the system fits a proper model on held-out data instead.
3. **The system learns.** A verifier's correction is remembered and reapplied automatically the next time the same misreading would happen — proven by an automated test, not just claimed.
4. **Tamper-evident audit trail.** Every action is hash-chained to the one before it; editing or deleting a past entry is detectable.
5. **Citizen-facing, not just office-facing.** The public verify page reads a record aloud (Hindi or English) for someone who reads with difficulty, and a kiosk-mode camera scan works from any device, not just a citizen's own smartphone.
6. **Actually deployed.** Not just "it runs on my laptop" — a real AWS EC2 instance, Docker Compose, Postgres, live right now.

Full version with more detail and every number's source: `docs/usps.md`.

---

## Slide: "Honest limitations" (include this — it builds credibility, not doubt)

- All measured numbers above are on **synthetic data** — no real land record has been tested yet (though the tool to do so exists: `/real-samples` in the app).
- Phone photos are the weakest input; it's a recognition-model limitation, not something more preprocessing fixes.
- About half of remaining field errors are a *confidently wrong* reading (e.g. `1805/1` misread as `1305/1` at 0.95 confidence) — re-reading doesn't catch this.
- Master data's Hindi village spellings (the original 4 Devanagari-script states) are algorithmically transliterated, not verified by a native speaker; Andhra Pradesh coverage is partial (~54% district, ~7% tehsil, ~2% village).
- Speed is 30–60s/page on CPU; 1–2s on GPU (no GPU available to test on).
- Read-aloud and the kiosk QR scan pass automated checks but haven't been confirmed by a person with real audio/a real camera yet.

Full list: `README.md`'s "Honest limitations" section.

---

## Slide: "Live demo"

**http://65.2.234.77:8000** — AWS EC2 (t3.medium, Mumbai region), Docker Compose, Postgres, encrypted volume, Elastic IP.

Demo accounts: `operator`/`upload@123`, `verifier`/`verify@123`, `admin`/`admin@123`.

If a network blocks the raw IP: `http://ec2-65-2-234-77.ap-south-1.compute.amazonaws.com:8000`

---

## Where every number came from (for Q&A prep)

| Claim | Source file |
| --- | --- |
| All accuracy/CER numbers | `eval/results/test.md`, `dev.md`, `multi.md` |
| Classifier confusion matrix | `eval/results/classification.md` |
| Phone-photo accepted/rejected split | `docs/usps.md`, section 2 |
| Which OCR changes were adopted vs rejected, and why | `eval/results/experiments.md` (13 experiments, each with a number) |
| Master data village/district/state counts | `backend/extraction/master/gazetteer.json` (run `python -c "import json; g=json.load(open('backend/extraction/master/gazetteer.json',encoding='utf-8')); print(len(g['states']))"` to reproduce) |
| Live deployment details | `DEPLOYMENT.md` |
| Full USP writeups with every number sourced | `docs/usps.md` |
| Test counts | `python -m pytest tests -q` (backend), `cd frontend && npm test` (frontend) |

Reproduce any number yourself: `python eval/evaluate.py --split test` (or `dev`/`multi`).
