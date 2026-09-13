# Data contracts between tracks

These are the only shapes each track can rely on from its neighbour. Change them only after telling the other tracks.

## A → B: OCR output (`backend/ocr` → `backend/extraction`)

```json
{
  "engine": "easyocr",
  "languages": ["hi", "en"],
  "elapsed_ms": 4210,
  "pages": [
    {
      "page": 1,
      "width": 1240,
      "height": 1754,
      "image_path": "storage/<doc_id>/page-1.png",
      "preprocess": {"deskew_angle": -1.8, "steps": ["grayscale", "illumination", "rotate90", "deskew", "denoise", "clahe", "rotate180"]},
      "quality": {"verdict": "poor", "median_confidence": 0.09, "sharpness": 212.4, "text_height_px": 11.0,
                  "tokens": 28, "advice": ["image is blurred - hold the camera steady, tap to focus and retake"]},
      "tokens": [
        {"text": "खाता संख्या", "confidence": 0.91, "bbox": [102, 340, 260, 372]}
      ],
      "lines": [
        {"text": "खाता संख्या : 00245", "confidence": 0.88, "bbox": [102, 340, 520, 372], "token_ids": [0, 1, 2]}
      ]
    }
  ]
}
```

* `bbox` is `[x0, y0, x1, y1]` in pixels of the **preprocessed** page image (`image_path`), so the frontend can draw boxes on the same image.
* `confidence` is always `0..1`.
* `tokens` are what the engine returned; `lines` are tokens grouped by vertical overlap, left to right.
* `preprocess.steps` records what was done. `rotate90` means the page was photographed sideways; `rotate180` means it was upside down (fixed after a recognition-confidence check).
* A page whose first reading is not `good` is read a second time with lighter denoising (h=5) and that
  reading is kept; `steps` then contains `denoise h5` and ends with `second read`. Pages that read well
  are read once. Turn it off with `LL_OCR_RETRY_SOFT=0`.
* Number tokens that read unsurely are read a second time by an **english-only** recogniser
  and replaced when it is clearly more confident; `steps` then contains `numbers:<how many>`.
  Only tokens written in Latin digits, or holding a letter no number can contain, are offered:
  a date that came out as `०२/०३/२००२` is already right and is left alone, and so is anything
  with a Devanagari letter in it (`1124/6क`). Poor pages are skipped entirely - there the
  english reader answers confidently with digits that are not on the page. `LL_OCR_NUMBER_PASS=0`
  turns it off.
* `quality.verdict` is `good` / `fair` / `poor` (thresholds from the dev set: median token confidence < 0.2 gave no correct fields, 0.2–0.4 was unreliable). `advice` holds plain-language retake tips. **Surface `poor` pages to the operator right after upload (L3), and route them to review with the advice as the reason (L2).**

## B → C: extraction output (`backend/extraction` → `backend/api`)

```json
{
  "document_type": "khatauni",
  "fields": {
    "khata_number": {
      "value": "00245",
      "raw": "OO245",
      "confidence": 0.86,
      "ocr_confidence": 0.91,
      "label_score": 1.0,
      "rule_score": 1.0,
      "valid": true,
      "issues": [],
      "page": 1,
      "bbox": [300, 340, 520, 372],
      "source": "same_line"
    }
  },
  "missing": ["registration_number"],
  "overall_confidence": 0.83,
  "route": "review",
  "route_reasons": ["low confidence: owner_name (0.62)"],
  "consistency": [{"check": "tehsil_in_district", "ok": true, "detail": "Sadar ∈ Lucknow"}]
}
```

* Field names are exactly the ones in `backend/extraction/schema.py`.
* `route` is `auto_accept` or `review`. See `backend/extraction/confidence.py` for the rule.
* A place field (`village`/`tehsil`/`district`/`state`) matched against the master gazetteer
  carries `normalized.hi_verified`: `true` for state/district/tehsil (hand-checked real Hindi),
  `false` for every village today (Hindi comes from `backend/extraction/transliterate.py`, a
  rule-based guess - see that module's docstring for its measured accuracy). **Any UI showing
  a village's Hindi name should visually flag it when `hi_verified` is `false`**, so a verifier
  never mistakes a machine transliteration for the official spelling.
* `plot_area.value` is normalised to a string like `"0.412 hectare"`; the numeric hectares go in `plot_area.normalized`.
* `owners` and `parcels` (top-level, alongside `fields`) hold every co-owner and every khasra
  row found under one khata. The single `fields.owner_name` / `fields.father_name` /
  `fields.khasra_number` / `fields.plot_area` / `fields.land_classification` always equal
  entry `[0]` of these lists, so existing consumers that only read `fields` keep working.

  ```json
  "owners": [
    {"owner_name": "Ram Prasad Sharma", "father_name": "Mohan Lal Sharma"},
    {"owner_name": "Shyam Lal Sharma", "father_name": null}
  ],
  "parcels": [
    {"khasra_number": "123/1", "plot_area": "0.5 hectare", "plot_area_normalized": {"value": 0.5, "unit": "hectare", "hectares": 0.5}, "land_classification": "agricultural_irrigated"},
    {"khasra_number": "456/2", "plot_area": "1.2 hectare", "plot_area_normalized": {"value": 1.2, "unit": "hectare", "hectares": 1.2}, "land_classification": "barren"}
  ]
  ```

  `owners`/`parcels` have exactly one entry when the document only has one owner/row.
  Names are split on `,` / `एवं` / `व` / `and` / `&` — whole-word only, never mid-word.
  The dataset generator (`data/generator/generate.py`) writes the same `owners`/`parcels`
  shape into ground-truth JSON for the `khatauni_table` template (1-3 owners, 1-4 rows).

## A → C: land-document classification (`backend/classify` → `backend/api/processing.py`)

Runs on the OCR output **before** extraction. A page that is not a land record never reaches
the extractor, so no field can be invented for it.

```json
{
  "is_land_document": true,            // false = rejected; null = undetermined (page unreadable)
  "confidence": 0.97,                  // the evidence balance squashed to 0..1, not a chosen number
  "evidence": {"parcel identifier": ["खसरा", "khata"], "extent": ["हेक्टेयर"], "revenue office": ["tehsil"]},
  "evidence_kinds": 3,                 // a page needs at least LL_CLASSIFY_MIN_GROUPS (2) *kinds*
  "evidence_against": {},              // invoice / certificate / bank / news / identity / medical words
  "government_indicators": ["government of", "revenue department"],  // reported, never credited
  "scripts": ["Devanagari", "Latin"],  // writing systems on the page - script, not language
  "words": 214,
  "document_type": "khatauni",         // or "unknown": a land record whose type we cannot name
  "type_family": "record_of_rights",   // khatauni / jamabandi / khatiyan / pahani are one family
  "type_candidates": ["khatauni", "record_of_rights"],
  "document_type_confidence": 0.9,
  "reason": "3 kinds of land evidence on the page",
  "undetermined": false
}
```

* `is_land_document: false` puts the document in status `not_land`, with **no fields**, and it never
  enters the verification queue. The UI shows *NOT A LAND DOCUMENT* with the reason.
* `null` (undetermined) means the quality check called the page `poor`, or fewer than 12 words were
  read: that is a quality problem, not a verdict, so the page goes on to review with retake advice.
* `document_type: "unknown"` is **not** a rejection: extraction continues generically and the
  screen says *manual review recommended*. The list of types is `DOCUMENT_TYPES` in
  `backend/classify/land.py`, and the family map beside it.
* Never one keyword: "survey" alone, "area" alone or "Government" alone is not evidence. A
  government seal on a marksheet does not make it a land record. Authenticity is never claimed.
* Stored on `documents.classification`; returned as `classification` on `GET /api/documents/{id}`.

## C → D: REST API

The live, typed list is at `http://localhost:8000/docs` (FastAPI auto-docs). Main groups:

| Group | Endpoints |
| --- | --- |
| auth | `POST /api/auth/login`, `GET /api/auth/me` |
| documents | `POST /api/documents`, `GET /api/documents`, `GET /api/documents/{id}`, `GET /api/documents/{id}/pages/{n}` |
| review | `GET /api/review/queue`, `POST /api/documents/{id}/verify`, `POST /api/documents/{id}/dispute` |
| admin | `GET /api/admin/stats`, `GET /api/admin/audit`, `GET/POST /api/admin/users`, `GET/POST /api/admin/real-samples` |
| integration (mock) | `/api/integration/lrms/*`, `/api/integration/dilrmp/*`, `/api/integration/gis/*` |
| public | `GET /api/public/records/{id}/verify` (no login - the QR code on a printed extract) |

Roles: `operator` (upload, view own), `verifier` (+ review queue, verify, dispute), `admin` (everything, including real-sample uploads).

`POST /api/documents/{id}/dispute` sends a `verified` document back to `needs_review`: every
field resets to `pending` for re-confirmation, and the dispute (with its required note) is
logged to the same hash-chained audit trail as a verify or reject decision.

`POST /api/admin/real-samples` uploads a real document plus typed ground truth (`multipart/form-data`:
`file` + a `ground_truth` JSON string shaped like `data/real/README.md`), runs the same
extraction pipeline a live upload gets, and returns per-field accuracy immediately - the file
and ground truth are also saved into `data/real/`, so `eval/evaluate.py --split real` picks up
every sample added this way too. `GET /api/admin/real-samples` lists what has been added.

Items from `GET /api/review/queue` and `GET /api/documents` carry `flagged`: how many of that
document's fields are still pending and below the auto-accept threshold or failing a rule, the
same rule the review screen uses to mark a field for checking (0 once a document is reviewed).
