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
