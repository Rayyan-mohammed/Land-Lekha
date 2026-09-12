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

## C → D: REST API

The live, typed list is at `http://localhost:8000/docs` (FastAPI auto-docs). Main groups:

| Group | Endpoints |
| --- | --- |
| auth | `POST /api/auth/login`, `GET /api/auth/me` |
| documents | `POST /api/documents`, `GET /api/documents`, `GET /api/documents/{id}`, `GET /api/documents/{id}/pages/{n}` |
| review | `GET /api/review/queue`, `POST /api/documents/{id}/verify` |
| admin | `GET /api/admin/stats`, `GET /api/admin/audit`, `GET/POST /api/admin/users` |
| integration (mock) | `/api/integration/lrms/*`, `/api/integration/dilrmp/*`, `/api/integration/gis/*` |

Roles: `operator` (upload, view own), `verifier` (+ review queue, verify), `admin` (everything).

Items from `GET /api/review/queue` and `GET /api/documents` carry `flagged`: how many of that
document's fields are still pending and below the auto-accept threshold or failing a rule, the
same rule the review screen uses to mark a field for checking (0 once a document is reviewed).
