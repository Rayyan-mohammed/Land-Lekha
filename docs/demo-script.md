# Live demo script (about 7 minutes)

Before judges arrive:

- [ ] `python -m uvicorn backend.api.main:app --port 8000` running, `/api/health` shows `"ocr_ready": true`
- [ ] frontend open at http://localhost:5173 (or the built app at http://localhost:8000)
- [ ] fresh database: `powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Fresh` (or stop the server, delete `storage/`, start again)
- [ ] `data/demo/` open in a file window; `data/demo/expected.md` open on the presenter's laptop
- [ ] one **unseen** document ready: `python data/generator/generate.py --count 1 --split unseen --seed <any new number>`

## 1. The problem (30 s)
Land records sit in handwritten registers and old scans, and they get retyped by hand. That's slow, and it introduces errors in exactly the fields that matter: owner, khasra, area.

## 2. Upload (1 min) — log in as `operator`
- Drag in `01-ror-english-clean.jpg`, `02-khatauni-table-scan.jpg`, `03-form-handwritten.jpg`, `07-sideways-photo.jpg` and `08-born-digital.pdf`.
- Point out: works on a phone too (the **Take photo** button), and takes PDF, JPG and TIFF.
- Click **हिंदी** in the sidebar: every screen, message, reason and date switches to Hindi, and back with one click.
- **`08-born-digital.pdf` is done in about a second**: PDFs exported by a land portal already contain the text, so no OCR is needed and the text is exact.
- **`07-sideways-photo.jpg`** was photographed sideways: it's turned upright automatically and reads as well as `01`.
- If a photo is too blurred, the upload screen says so straight away (**poor quality, with what to fix and a request to retake**), so the operator fixes it at the counter instead of creating a case nobody can resolve. `05-phone-photo.jpg` shows the check.
- While it runs: *"preprocessing → OCR in Hindi and English → field extraction → validation against master data → confidence scoring"*.

## 3. What the machine decided (2 min) — log in as `verifier`
- The born-digital PDF (`08`) is **auto-accepted**: every field passed validation above the calibrated threshold.
- The English Record of Rights (`01`) needs **one field** checked (the father's name); everything else is trusted. Most documents land in between: a handful of flagged fields, not a full retype.
- Open the handwritten form from the **review queue**:
  - Left: the cleaned, deskewed scan with a box on every field (green = confident, amber or red = check it).
  - Right: each value, the raw OCR text, and *why* it was flagged.
  - Places are checked against the master database (village ∈ tehsil ∈ district).
- Correct one flagged value and **Approve**. Say: *"the verifier doesn't retype the document, they check one or two fields"*.
- Mention: the correction is stored, and the same misreading is fixed automatically next time (the learning loop).
- Upload and open **`09-multi-owner-khatauni.jpg`**: one khata, three co-owners, three khasra rows. The review screen lists every co-owner with their father's name, and every parcel row. Real Khataunis look like this; a single "owner" field would lose two of the three owners.

## 4. Governance (1 min) — log in as `admin`
- **Dashboard**: documents processed, auto-accept rate, pending verification, error statistics, state- and district-wise progress, benchmark CER and field accuracy.
- **Records & GIS**: the verified record in LRMS exchange format with every co-owner and parcel row, **Push** to LRMS (simulated acknowledgement), the parcel on the map, the DILRMP progress report, and a **CSV** download of the list for the tehsil office.
- Open **Extract** on a record: the printed copy is bilingual (English and Hindi) with a QR code. Scan it with a phone: the public check page says whether the paper still matches the record, in both languages.
- **Audit trail**: every upload, decision and correction, with who, when and from which IP.
- `http://localhost:8000/docs`: the documented REST API other government systems would call.

## 5. The unseen document (1 min)
Upload the document nobody has seen. Whatever happens, explain it: confident fields pass, uncertain ones are flagged, nothing is silently guessed.

## Numbers to quote
From `eval/results/test.md` (40 held-out synthetic documents; calibrated on a separate dev split): **84.4% field accuracy, 21.8% of fields flagged for a human, 96.2% precision on unflagged fields, 3/3 auto-accepted documents fully correct, median CER 11.1%**, on real LGD village names. Weakest case: phone photos (43.9%).

## Honest answers to likely questions
- **"What about blurred phone photos?"** The text is found but the letters are too blurred for the recogniser. We measured this: pages with a median OCR confidence below 0.2 produced no correct fields. So instead of guessing, the app asks the operator to retake the photo. A recognition model trained on real field photos is on the roadmap.
- **"Is the data real?"** No. No public labelled dataset of Indian land records exists, so we generate realistic Khatauni, Khasra, Jamabandi and Khatiyan records, with ground truth, in Hindi and English. They include handwriting fonts, Devanagari digits, fading, stains, skew and phone-photo perspective. Real records are the first thing we'd add after selection.
- **"Is LRMS/DILRMP integration real?"** The APIs are real and documented; the external government systems are simulated because we have no access to them.
- **"Handwriting?"** Handwriting-style entries work when legible. Truly cursive registers need fine-tuning on real Indic handwriting data (roadmap).
- **"Why trust the confidence?"** It is a logistic model calibrated on held-out data. Raw OCR confidence is badly calibrated for Devanagari: correct text often scores 0.4–0.6.
