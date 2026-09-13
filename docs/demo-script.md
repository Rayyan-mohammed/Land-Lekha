# Live demo script (about 7 minutes)

Before judges arrive:

- [ ] `python -m uvicorn backend.api.main:app --port 8000` running, `/api/health` shows `"ocr_ready": true`
- [ ] frontend open at http://localhost:5173 (or the built app at http://localhost:8000)
- [ ] fresh database: `powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Fresh` (or stop the server, delete `storage/`, start again)
- [ ] `data/demo/` open in a file window; `data/demo/expected.md` open on the presenter's laptop
- [ ] one **unseen** document ready: `python data/generator/generate.py --count 1 --split unseen --seed <any new number>`
- [ ] on the actual laptop/browser you'll present with: open a verified extract's QR page once, press **read aloud** and actually listen, then open `/verify` and scan a printed QR with the real camera. Both are built and pass their automated tests, but neither has been confirmed working with real audio or a real camera before now - find out here, not on stage.

## 1. The problem (30 s)
Land records sit in handwritten registers and old scans, and they get retyped by hand. That's slow, and it introduces errors in exactly the fields that matter: owner, khasra, area.

## 2. Upload (1 min) — log in as `operator`
- Drag in `01-ror-english-clean.jpg`, `02-khatauni-table-scan.jpg`, `03-form-handwritten.jpg`, `07-sideways-photo.jpg` and `08-born-digital.pdf`.
- Point out: works on a phone too (the **Take photo** button), and takes PDF, JPG and TIFF.
- Click **हिंदी** in the sidebar: every screen, message, reason and date switches to Hindi, and back with one click.
- **`08-born-digital.pdf` is done in about a second**: PDFs exported by a land portal already contain the text, so no OCR is needed and the text is exact.
- **`07-sideways-photo.jpg`** was photographed sideways: it's turned upright automatically and reads as well as `01` (which is the same record — see the duplicate catch below).
- If a photo is too blurred, the upload screen says so straight away (**poor quality, with what to fix and a request to retake**), so the operator fixes it at the counter instead of creating a case nobody can resolve. `05-phone-photo.jpg` shows the check: it is read twice (once with lighter denoising), still comes back unreadable, and is sent back for a retake rather than guessed at. Being read twice, it also takes about twice as long as a clean page.
- With several files, the summary line above the list says how many were accepted, sent to a verifier or need a retake; a file uploaded twice is recognised and linked, not processed again. On a computer, a screenshot can be pasted straight in with **Ctrl+V**.
- While it runs: *"preprocessing → OCR in Hindi and English → field extraction → validation against master data → confidence scoring"*.

## 3. What the machine decided (2 min) — log in as `verifier`
- Two of them are **auto-accepted**: the born-digital PDF (`08`) and the English Record of Rights (`01`) — every field passed validation above the calibrated threshold.
- **`07-sideways-photo.jpg` is the same record as `01`**, photographed sideways. It is turned upright and read just as well (nothing to check on it), and then held for a verifier as a **possible duplicate** — same village and khasra, same khata, the owner's name identical. Say this plainly: the second copy of a record is caught by what is *on* the page, not by the file being the same file.
- The others need **one to three fields** checked each, not a full retype: `02` three, `03` two, `04` three, `06` one, `09` three. Each takes a verifier seconds.
- The **review queue** shows how many fields each document needs checked; switch it to **Fewest fields first** to clear quick ones, and the dashboard says exactly how many fields are waiting in all.
- Open the handwritten form from the **review queue**:
  - Left: the cleaned, deskewed scan with a box on every field (green = confident, amber or red = check it).
  - Right: each value, the raw OCR text, and *why* it was flagged.
  - Places are checked against the master database (village ∈ tehsil ∈ district).
- Correct one flagged value and **Approve**. Say: *"the verifier doesn't retype the document, they check one or two fields"*.
- Point at the **Flag for re-verification** button on that now-verified document: *"if an officer spots something wrong later, they can send it back with a note - every field reopens for re-confirmation, and the dispute itself lands in the same audit trail as the approval."* No need to actually click it unless there's time.
- Mention: the correction is stored, and the same misreading is fixed automatically next time (the learning loop). If a judge
  pushes on it, run the test in front of them — it corrects one owner's name, sends in a second document misread the same
  way, and asserts the fix arrived with no person involved:
  `python -m pytest tests/test_api.py -k carried_over -q` (about 6 seconds, no OCR model needed).
- Close the tab halfway through a review and open the document again: the unsaved corrections come back, so nothing is lost if the power or the connection drops. **Skip** leaves a hard document for later without losing those corrections.
- Upload and open **`09-multi-owner-khatauni.jpg`**: one khata, three co-owners, three khasra rows. The review screen lists every co-owner with their father's name, and every parcel row. Real Khataunis look like this; a single "owner" field would lose two of the three owners.

## 4. Governance (1 min) — log in as `admin`
- **Dashboard**: documents processed, auto-accept rate, pending verification, error statistics, state- and district-wise progress - including a live map, circles sized by volume and coloured by share digitized - benchmark CER and field accuracy, and an estimated time saved (say plainly it is a stated assumption, not a measurement).
- **Documents**: filter to one status (or search a district) and press **CSV** — the day's list for a progress report, with status, confidence and fields still to check. The status bars on the dashboard open the same filtered list.
- **Records & GIS**: the verified record in LRMS exchange format with every co-owner and parcel row, **Push** to LRMS (simulated acknowledgement), the parcel on the map, the DILRMP progress report, and a **CSV** download of the list for the tehsil office. Press **Not sent to LRMS**, then **Send all to LRMS**: the day's backlog goes in one click, with one summary message.
- Open **Extract** on a record: the printed copy is bilingual (English and Hindi) with a QR code. Scan it with a phone: the public check page says whether the paper still matches the record, in both languages - press **Read in Hindi** or **Read in English** and it reads the record aloud, for a citizen who reads with difficulty. Then open `/verify` on any device and scan the same QR with its camera directly: a kiosk mode for a tehsil-office terminal, not only a citizen's own phone.
- **Audit trail**: every upload, decision and correction, with who, when and from which IP. Filter by person or by kind of event, and press **CSV** to keep a copy for the compliance file.
- If there is time, open the app on a phone: the lists turn into cards, the review screen has a **Go to fields** button above the scan, and the QR check on a printed extract works without signing in.
- `http://localhost:8000/docs`: the documented REST API other government systems would call.

## 5. The unseen document (1 min)
Upload the document nobody has seen. Whatever happens, explain it: confident fields pass, uncertain ones are flagged, nothing is silently guessed.

Every upload now shows its verdict first: **✓ LAND DOCUMENT** with a confidence, the document type (or *unknown — manual review recommended*, which still goes forward), the scripts on the page, and the kinds of evidence it found. Government or revenue wording is reported as an *indicator* — the screen says in as many words that this is not proof of authenticity.

If someone hands you a page that is **not** a land record at all — an invoice, a letter, a photo of anything — upload it. The page is read, classified **before** any field is extracted, and comes back as **✕ NOT A LAND DOCUMENT** with its confidence and the counter-evidence it saw ("reads like invoice"). No fields are invented, nothing reaches the register, and it never enters the verifier's queue. A newspaper page and a school marksheet were both tried live: 99% not a land document. That behaviour is held in place by `tests/test_api.py::test_a_page_that_is_not_a_land_record_invents_nothing`.

## Numbers to quote
From `eval/results/test.md` (40 held-out synthetic documents; calibrated on a separate dev split): **88.1% field accuracy, 15.3% of fields flagged for a human, 96.4% precision on unflagged fields, 11 of 13 auto-accepted documents fully correct, median CER 10.9%**, on real LGD village names. Weakest case: phone photos (56.5%).

## Honest answers to likely questions
- **"What about blurred phone photos?"** The headline number is 56.5%, and it mixes two different things. Of the 17 phone photos across our three splits, the quality check accepted 12 — those average **84.3% of fields**, the worst 63.6%. It sent the other 5 back for a retake, and those average 10.4%, the best of them 21.4%. The two groups do not overlap: the system knows which photos it cannot read. A page that reads badly is read a second time with lighter denoising, which recovers part of it — two dev photos that gave nothing at all now give some fields. When even the second read is poor the app asks the operator to retake the photo instead of guessing. A recognition model trained on real field photos is on the roadmap.
- **"Is the data real?"** No. No public labelled dataset of Indian land records exists, so we generate realistic Khatauni, Khasra, Jamabandi and Khatiyan records, with ground truth, in Hindi and English. They include handwriting fonts, Devanagari digits, fading, stains, skew and phone-photo perspective. Real records are the first thing we'd add after selection - there's already an admin screen (`/real-samples`) where anyone can upload a real document, type in the correct values, and see the accuracy right there; we just haven't had a real document to put through it yet.
- **"Is LRMS/DILRMP integration real?"** The APIs are real and documented; the external government systems are simulated because we have no access to them.
- **"Handwriting?"** Handwriting-style entries work when legible. Truly cursive registers need fine-tuning on real Indic handwriting data (roadmap).
- **"Why trust the confidence?"** It is a logistic model calibrated on held-out data. Raw OCR confidence is badly calibrated for Devanagari: correct text often scores 0.4–0.6.
- **"Why are numbers the hard part?"** Hindi and English digits look alike, and one model that knows both will answer `/q०/4` where the page says `190/4`. A number that reads unsurely is read once more by a reader that knows English digits only; on the held-out split that lifted survey numbers by 7.7 points and khata numbers by 5. A number already written in Devanagari digits is left alone — it is usually right, and that reader would only guess at it.
