# Live demo script (about 6 minutes)

Before judges arrive:

- [ ] `python -m uvicorn backend.api.main:app --port 8000` running, `/api/health` shows `"ocr_ready": true`
- [ ] frontend open at http://localhost:5173 (or the built app at http://localhost:8000)
- [ ] fresh database: stop the server, delete `storage/`, start again
- [ ] `data/demo/` open in a file window; `data/demo/expected.md` open on the presenter's laptop
- [ ] one **unseen** document ready: `python data/generator/generate.py --count 1 --split unseen --seed <any new number>`

## 1. The problem (30 s)
Land records sit in handwritten registers and old scans, and they get retyped by hand. That's slow, and it introduces errors in exactly the fields that matter: owner, khasra, area.

## 2. Upload (1 min) — log in as `operator`
- Drag in `01-ror-english-clean.jpg`, `02-khatauni-table-scan.jpg` and `03-form-handwritten.jpg`.
- Point out: works on a phone too (the **Take photo** button), and takes PDF, JPG and TIFF.
- While it runs: *"preprocessing → OCR in Hindi and English → field extraction → validation against master data → confidence scoring"*.

## 3. What the machine decided (2 min) — log in as `verifier`
- The English Record of Rights is **auto-accepted**: every field passed validation above the calibrated threshold.
- Open the handwritten form from the **review queue**:
  - Left: the cleaned, deskewed scan with a box on every field (green = confident, amber or red = check it).
  - Right: each value, the raw OCR text, and *why* it was flagged.
  - Places are checked against the master database (village ∈ tehsil ∈ district).
- Correct one flagged value and **Approve**. Say: *"the verifier doesn't retype the document, they check one or two fields"*.
- Mention: the correction is stored, and the same misreading is fixed automatically next time (the learning loop).

## 4. Governance (1 min) — log in as `admin`
- **Dashboard**: documents processed, auto-accept rate, pending verification, error statistics, state- and district-wise progress, benchmark CER and field accuracy.
- **Records & GIS**: the verified record in LRMS exchange format, **Push** to LRMS (simulated acknowledgement), the parcel on the map, and the DILRMP progress report.
- **Audit trail**: every upload, decision and correction, with who, when and from which IP.
- `http://localhost:8000/docs`: the documented REST API other government systems would call.

## 5. The unseen document (1 min)
Upload the document nobody has seen. Whatever happens, explain it: confident fields pass, uncertain ones are flagged, nothing is silently guessed.

## Numbers to quote
These come from `eval/results/test.md`: 40 held-out synthetic documents, calibrated on a separate dev split.

## Honest answers to likely questions
- **"Is the data real?"** No. No public labelled dataset of Indian land records exists, so we generate realistic Khatauni, Khasra, Jamabandi and Khatiyan records, with ground truth, in Hindi and English. They include handwriting fonts, Devanagari digits, fading, stains, skew and phone-photo perspective. Real records are the first thing we'd add after selection.
- **"Is LRMS/DILRMP integration real?"** The APIs are real and documented; the external government systems are simulated because we have no access to them.
- **"Handwriting?"** Handwriting-style entries work when legible. Truly cursive registers need fine-tuning on real Indic handwriting data (roadmap).
- **"Why trust the confidence?"** It is a logistic model calibrated on held-out data. Raw OCR confidence is badly calibrated for Devanagari: correct text often scores 0.4–0.6.
