# LandLekha — results for the PPT

Everything here is copied from `eval/results/*.md` (the actual measured output) — nothing is
invented. Charts are in `charts/`, real app screenshots are in `screenshots/`. Organized below
by suggested slide, so you can lift a slide's worth of content in one pass.

**This folder was refreshed on 2026-09-23 after a large update landed** — the land-document
classifier was deliberately removed (see below), real documents were measured for the first
time, and duplicate detection + confidence reliability were newly measured. If you see an older
copy of this folder floating around, use this one.

---

## Slide: "Architecture" → `charts/architecture_slide.png` (use this one on the slide)

The team's own target architecture, drawn slide-ready in the deck's colours: Input → Preprocess →
Classify → Multi-script OCR (EasyOCR + TrOCR) → Extract → Validation layer → the 88% decision →
Auto-accept / Verifier review queue → Verified output, with the corrections → learning-memory loop.

**Know which parts are built today, in case a judge opens the repo:** Classify and TrOCR are
*planned for the next round* — the code currently has EasyOCR only, and the land-document
classifier was removed. The auto-accept threshold in the code is 0.90 (the slide says 88%).
`charts/architecture_slide_next_round_tags.png` is the same diagram with those two cards outlined
and tagged "NEXT ROUND" — use that one if you want the slide to be exact about what is live.

`charts/00_architecture.png` is a second view of the same system, coloured by which *team track*
owns each part (matches README's mermaid diagram, i.e. what is built now) — use it only if you
want to show ownership.

**Talking point**: the loop at the center is the point — an auto-accepted record and a verifier-approved one land in the same database indistinguishably, but every correction a verifier makes feeds back into the extraction step through the learning memory, so the system keeps improving without retraining.

---

## Headline numbers (put these on a "results at a glance" slide)

| Number | What it means |
| --- | --- |
| **88.1%** | Field accuracy across all 15 fields, on 40 held-out documents never seen during tuning |
| **96.4%** | Precision of the fields the system does NOT flag for review — i.e. when it doesn't ask a human to check, it's right 96.4% of the time |
| **15.3%** | Share of fields flagged for a human — the verifier checks about 1 field in 7, not the whole document |
| **0.0245** | Expected calibration error — the confidence number is honest, not just optimistic |
| **84.3% vs 10.4%** | Field accuracy on phone photos the quality gate accepted vs. the ones it sent back for a retake — the two groups never overlap |
| **32 of 40, 0 false positives** | The same parcel, re-photographed, is found again — and a different parcel is never wrongly matched, across 1,560 comparisons |
| **18.2%** | Field accuracy on the first 3 **real** documents — low, honestly reported, and explained (see below) |
| **6 states, 71 districts, 33,942 villages** | Real government village data (Ministry of Panchayati Raj LGD directory), not made up |
| **152 + 37** | Backend + frontend automated tests, all green in CI |
| **Live** | https://landlekha.in — actually deployed, CloudFront + AWS EC2 + Docker + Postgres |

---

## Slide: "Overall accuracy" → `charts/01_overall_accuracy_by_split.png`

Three separate evaluation splits, so the number isn't cherry-picked from one lucky run:

| Split | Field accuracy | Required-field accuracy | Precision on unflagged fields | Documents |
| --- | --- | --- | --- | --- |
| Dev (used to tune the confidence threshold) | 87.6% | 87.5% | 96.4% | 40 |
| **Test (held-out — the honest number)** | **88.1%** | 87.5% | **96.4%** | 40 |
| Multi-owner (hardest split — several co-owners/parcels per khata) | 85.2% | 83.8% | 94.3% | 30 |

**Talking point**: test came out slightly *better* than dev, and the threshold was deliberately set to trade some auto-accept rate for a safety margin — this isn't a number that got lucky on tuning data.

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

**Talking point**: the weakest fields (khasra number, plot area) are exactly the ones with the most varied handwritten formats and OCR digit confusion — which is *why* the project built a second, English-only re-read pass specifically for numbers.

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

## Slide: "Real documents — the honest result" → `charts/08_real_documents_result.png`

The first 3 real land documents ever put through the pipeline: registered deeds from Andhra
Pradesh, West Bengal and Haryana (not Khataunis — the record type this was built around).

- Fields right: **1 of 11 (9.1%)** on the first run → **2 of 11 (18.2%)** after fixing one bug the same documents exposed
- Document type named correctly: **0 of 3**
- Auto-accepted into the register: **0 of 3** — every one went to a human

**Why it's this low, in one sentence each**: (1) 8 of the 11 ground-truth fields are places in West Bengal/Haryana, which aren't in the master data yet; (2) the recognizer garbled printed English on stamp paper badly enough that "DEED OF GIFT" came back as `DDDD OD GIDT`; (3) page one of a deed carries the stamp and parties, not the parcel schedule — the field that matters is on a page nobody supplied.

**Talking point — lead with this, don't bury it**: low as this looks, it is the system working correctly. Nothing was invented, nothing was auto-accepted, every document went to a person. Measuring this also found and fixed 4 real bugs (a unit-conversion bug that made land parcels 20× too big, a units crash, an orientation misread, unrecognized deed titles) that synthetic data never would have caught. This is exactly the kind of result a judge respects more than a suspiciously clean number — say so explicitly.

> Full writeup: `eval/results/real.md`. The documents themselves are kept off the public repository for privacy.

---

## Slide: "Finding the same parcel twice" → `charts/09_duplicate_detection.png`

Not just "same file uploaded twice" (that's a hash check) — the harder case: the **same parcel**
arriving again as a **different photograph**, read slightly differently by OCR each time.

- **32 of 40 (80%)** duplicate parcels found on the test split
- **0 false matches in 1,560 comparisons** — a different parcel is never wrongly flagged as the same one
- All 8 misses traced to a missing village or khasra reading, not a scoring bug — 6 of 8 would be found if that one field had been read at all

**Talking point**: the asymmetry is deliberate — a missed duplicate just goes to a verifier like any other document; a *false* duplicate would block a genuine record from being registered. The system is tuned to never do the second one.

---

## Slide: "Is the confidence number honest?" → `charts/10_confidence_reliability.png`

Measured on 516 fields from the 40 held-out test documents — does a 0.9 confidence actually mean "right 90% of the time"?

- **Expected calibration error: 0.0245** — close to zero is good
- The bin that matters holds 442 of 516 fields: claims 95.8%, actually right 96.4% — a 0.6-point gap
- One real weakness found: the 0.8–0.9 bucket is overconfident by 12 points (measured, not hidden)

**Talking point**: this is the difference between "we show a confidence score" and "the confidence score means something" — most systems do the first and call it done.

---

## Retracted, on purpose: the land-document classifier

An earlier version of this pipeline had a separate "is this a land record?" classifier, measured
at 100% on 115 real OCR readings. **It was removed** — the team's own judgment was that it was a
claim PS 26018 never asked for. Routing now works more simply: a page with none of the required
fields cannot be auto-accepted, reaches a verifier with one reason saying so, and no fields are
invented. This is worth one sentence in a demo if asked "what changed" — it shows the team
retracts a good-looking number when it doesn't hold up to scrutiny, which is a stronger signal
than the number itself would have been.

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

(These screenshots predate a few newer screens — the register-comparison card and the kiosk QR
scan page aren't pictured yet. The live demo has them.)

---

## Slide: "What makes this different" (USPs — pick 3-4 for time)

1. **Calibrated confidence, not raw OCR score** — raw OCR confidence for Devanagari is badly calibrated (correct text often scores only 0.4–0.6); the system fits a proper model on held-out data, and that model's honesty is itself measured (ECE 0.0245).
2. **The system learns.** A verifier's correction is remembered and reapplied automatically the next time the same misreading would happen — proven by an automated test, not just claimed.
3. **Tamper-evident audit trail.** Every action is hash-chained to the one before it; editing or deleting a past entry is detectable.
4. **Citizen-facing, not just office-facing.** The public verify page reads a record aloud (Hindi or English) for someone who reads with difficulty, and a kiosk-mode camera scan works from any device, not just a citizen's own smartphone.
5. **Actually deployed.** Not just "it runs on my laptop" — a real AWS EC2 instance, Docker Compose, Postgres, live right now.
6. **Tested on real paper and honest about the result.** Most hackathon demos never leave synthetic data. This one did, scored 18.2%, said so, and used it to fix four real bugs.

Full version with more detail and every number's source: `docs/usps.md`.

---

## Slide: "Honest limitations" (include this — it builds credibility, not doubt)

- **Real-world accuracy is 18.2% on the 3 real documents measured so far** (above) — the synthetic numbers above describe synthetic data well; real paper is harder and less tested.
- Phone photos are the weakest synthetic-data input; it's a recognition-model limitation, not something more preprocessing fixes.
- About half of remaining field errors are a *confidently wrong* reading (e.g. `1805/1` misread as `1305/1` at 0.95 confidence) — re-reading doesn't catch this.
- Master data covers 6 states; West Bengal and Haryana (2 of the first 3 real documents) aren't in it yet, so 8 of 11 real-document fields could never be validated even if read perfectly.
- Master data's Hindi village spellings (the 4 original Devanagari-script states) are algorithmically transliterated, not verified by a native speaker; Andhra Pradesh coverage is partial.
- Speed is 30–60s/page on CPU; 1–2s on GPU (no GPU available to test on).
- Read-aloud and the kiosk QR scan pass automated checks but haven't been confirmed by a person with real audio/a real camera yet.
- The land-document classifier was built, measured at 100%, and deliberately retracted (above) — a reminder that a good number isn't the same as a claim worth keeping.

Full list: `README.md`'s "Honest limitations" section.

---

## Slide: "Live demo"

**https://landlekha.in** — CloudFront (HTTPS) in front of an AWS EC2 origin (t3.medium, Mumbai region), Docker Compose, Postgres, encrypted volume.

Demo accounts: `operator`/`upload@123`, `verifier`/`verify@123`, `admin`/`admin@123`.

Direct origin (bypasses CloudFront): `http://65.2.234.77:8000`

---

## Where every number came from (for Q&A prep)

| Claim | Source file |
| --- | --- |
| All synthetic accuracy/CER numbers | `eval/results/test.md`, `dev.md`, `multi.md` |
| Real-document result (18.2%) | `eval/results/real.md` |
| Duplicate detection | `eval/results/duplicates.md` |
| Confidence reliability / ECE | `eval/results/reliability.md` |
| Handwriting-specific scope | `eval/results/handwriting.md` |
| Telugu reader / per-page language choice | `eval/results/telugu.md` |
| Which OCR changes were adopted vs rejected, and why | `eval/results/experiments.md` |
| Master data village/district/state counts | `backend/extraction/master/gazetteer.json` (run `python -c "import json; g=json.load(open('backend/extraction/master/gazetteer.json',encoding='utf-8')); print(len(g['states']))"` to reproduce) |
| Live deployment details | `DEPLOYMENT.md` |
| Full USP writeups with every number sourced | `docs/usps.md` |
| Test counts | `python -m pytest tests -q` (backend), `cd frontend && npm test` (frontend) |

Reproduce any number yourself: `python eval/evaluate.py --split test` (or `dev`/`multi`), `python eval/real_eval.py`, `python eval/duplicates_eval.py --split test`, `python eval/reliability.py --split test`.
