# What makes LandLekha different

Written from what the code actually does and what the evaluation actually measured. Every number
here is reproducible from `eval/results/` or a named test. Anything that is a plan rather than a
result says so.

## The one-line pitch

Most "AI for land records" demos read a page and hand you fields. LandLekha is built around the
opposite claim: **the useful part is knowing which fields not to trust**, because a wrong khasra
number written into a register is worse than no number at all.

---

## The six USPs, strongest first

### 1. It knows what it cannot read, and proves it

The quality check separates readable pages from unreadable ones before anything is extracted.
Across all 17 phone photos in the three evaluation splits:

| Phone photos | Documents | Mean field accuracy | Range |
| --- | --- | --- | --- |
| accepted by the quality check | 12 | **84.3%** | 63.6% - 100% |
| sent back for a retake | 5 | 10.4% | 0% - 21.4% |

The two groups do not overlap. The worst page it kept scored 63.6%; the best page it rejected
scored 21.4%. A blurred photo is refused **at the counter**, with plain-language advice in Hindi
or English, instead of becoming a case nobody can resolve later.

Where it shows in the demo: upload `05-phone-photo.jpg`, watch it be read twice and still sent
back.

### 2. Calibrated confidence, not a raw OCR score

Measured, not claimed: expected calibration error **0.0245** on 516 held-out fields, and at the shipped
threshold of 0.90 we accept 85.7% of fields with 3.6% of those wrong - moving to 0.95 halves the risk and
hands a third of the fields back to a person ([eval/results/reliability.md](../eval/results/reliability.md)).

Raw OCR confidence is badly calibrated for Devanagari - correct text often scores 0.4-0.6. Each
field's confidence is a logistic model over OCR, rule, label and source evidence, fitted on a
separate `dev` split. On 40 **held-out** documents:

- field accuracy **88.1%**, required-field accuracy 87.5%
- **15.3%** of fields flagged for a human - the verifier checks about 1 field in 7 rather than
  retyping the page
- of the fields left unflagged, **96.4%** are right
- a third of documents pass with no human at all

The threshold deliberately sits in the *middle* of the range that meets the 95% precision target,
not at its lowest edge - because the lowest edge met the target on the tuning split and missed it
on held-out data (`eval/results/experiments.md`, section 12). That decision cost auto-accept rate
and bought back the safety margin.

### 3. Two OCR passes that each fix a different, measured failure

Not "we used EasyOCR". Two changes, each A/B tested and each written up with the evidence:

- **A second read for pages that read badly.** Strong denoising erases strokes on blurred or faded
  paper, so a page whose first reading is not `good` is read again with lighter denoising. +2.2
  points of dev field accuracy; pages that read well are untouched.
- **Numbers re-read in English alone.** The combined Hindi+English model answers `/q०/4` where the
  page says `190/4`, because it can reach for Devanagari digits and look-alike letters. A number
  that reads unsurely is read again by a recogniser that has no Devanagari at all. On held-out
  data: survey numbers +7.7 points, khata numbers +5.0, handwritten entries +4.6. A number already
  written in Devanagari digits is left alone - it is usually right, and that reader would only
  guess at it.

Rejected experiments are written up too, with their numbers: cell-by-cell table reading, unsharp
masking, lighter denoising applied to every page, runtime selection between two readings.

### 4. Everything a verifier does is remembered, and everything anyone does is chained

- **Corrections are learned.** Correct one owner's name, and the next document misread the same way
  arrives already fixed, marked `learned`, with the original OCR text still on the record. That is
  not a claim: `tests/test_api.py::test_a_correction_is_carried_over_to_the_next_document` does
  exactly that in about six seconds, and fields that get corrected often have their thresholds
  raised automatically.
- **The audit trail is tamper-evident.** Each entry is hashed together with the one before it, so
  an entry edited or deleted afterwards stops matching, and `GET /api/admin/audit/verify` says
  which one. This is tamper-*evidence*, not tamper-proofing - signing the chain is the honest next
  step - but a silent rewrite is no longer silent.
- **A printed extract carries a fingerprint.** Anyone scanning its QR code sees, without logging
  in, whether the paper still matches the record.
- **A verified document can be reopened, not just overwritten.** An officer who spots something
  wrong after approval sends it back for a second look with a required note; every field resets
  for re-confirmation, and the dispute itself lands in the same hash-chained audit trail as
  everything else - reopening a record is as accountable as approving one.

### 5. Built for the office - and the citizen - it would actually run in

- **Hindi and English everywhere**, including error messages, flag reasons, retake advice, dates
  and screen-reader labels - with tests that fail the build if any on-screen string, any title
  handed to a component, or any new retake advice lacks Hindi.
- **Accessible and phone-shaped**: axe reports 0 violations across 11 screens in both languages,
  lists become cards on a phone, and every control is a thumb-sized target.
- **A citizen who cannot read well can still use the verification page.** It reads the verified
  record aloud, in Hindi or English, with the browser's own text-to-speech - no server round-trip.
- **No smartphone camera shortcut? No app? No problem.** A kiosk-mode scan page reads the same QR
  code with any camera - a tehsil-office terminal, not just a citizen's own phone.
- **Honest about a bad connection**: if the server disappears the app says so and keeps you signed
  in; unsaved corrections survive a reload; a half-reviewed document can be skipped and picked up.
- **Least privilege**: an operator uploads pages and sees their own uploads. They cannot browse the
  register, issue an extract, or read another operator's audit trail - through REST or GraphQL.

---

## What is an MVP feature and what is a differentiator

| Everyone will have | We also have |
| --- | --- |
| OCR of a scanned record | A quality gate that refuses pages it cannot read, with retake advice |
| Assumes every upload is a land record | A page with none of the required fields cannot be auto-accepted: it reaches a verifier with one reason saying so and no invented values |
| Fields pulled out of the text | Per-field calibrated confidence, and a measured precision for the fields left unflagged |
| A review screen | A review screen that says *why* each field was flagged, and remembers the correction |
| A verified record is final | A dispute flow that reopens it for a second look, logged to the same tamper-evident chain |
| "Validated against master data" | Real LGD village names: 33,942 villages, 1,331 tehsils, 71 districts, 6 states, with hierarchy checks (Telangana complete, Andhra Pradesh partial - see README's honest limits) |
| One owner per record | Every co-owner and every parcel row under one khata |
| An audit log | An audit log whose entries are hash-chained, with an endpoint that checks them |
| A REST API | REST **and** GraphQL over the same data, with the same access rules |
| English UI | Every string in Hindi and English, enforced by tests |
| A QR code you scan with your own phone | A kiosk mode that scans it from any camera, and reads the record aloud in Hindi or English |
| A progress table of numbers | The same progress plotted on a live map, sized and coloured by what it means |
| "We'll test on real data eventually" | An in-app tool to upload a real document, type the correct values, and see the accuracy immediately |

## The honest limits, stated before anyone asks

- **The data is synthetic.** No public labelled dataset of Indian land records exists, so the
  documents are generated with ground truth - handwriting fonts, Devanagari digits, fading,
  stains, skew, phone-photo perspective. Real records are the first thing to add.
- **Phone photos are the weakest input** (56.5% overall), which is why the quality gate exists.
- **About half the remaining field errors are a recogniser that is confidently wrong** - `1805/1`
  read as `1305/1` at 0.95 - which no amount of re-reading fixes. Fine-tuning on real Indic
  handwriting is the lever there.
- **LRMS / DILRMP / GIS integration is real APIs against simulated government systems**, because
  we have no access to the real ones.
- **Speed**: about 30-60 s per page on a CPU laptop, 1-2 s on a GPU, and 0.5 s for born-digital
  PDFs, which are read exactly from their text layer.
