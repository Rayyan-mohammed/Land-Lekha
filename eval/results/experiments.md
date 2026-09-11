# OCR experiments

Every OCR change is A/B-tested on the **dev** split with identical extraction code
(`python eval/compare.py --split dev ocr <experiment-cache>`). A change is adopted only if
it improves **field accuracy**, not only CER. The test split is used once, for the final report.

## 1. Smaller text-detection canvas (1280 → 1024 px) — rejected

Aim: detection is the slowest CPU step, and a 1024 px canvas halved detection time in an
isolated benchmark with a similar number of text boxes.

| | 1280 (baseline) | 1024 |
| --- | --- | --- |
| Field accuracy (17 docs) | 91.2% | 89.4% |
| CER median | 11.3% | 13.1% |

Accuracy dropped on every document type and the end-to-end time did not improve
measurably, so the run was stopped at 17 documents. Setting kept: `LL_OCR_CANVAS=1280`.

## 2. Adaptive sharpening of soft pages — not adopted (kept as an option)

Aim: phone photos and cheap scans are blurred. An unsharp mask is applied when the
page's edge sharpness (99.5th-percentile gradient after denoising) is below 450; clean
pages score about 850, and blurred pages 180–450. It triggered on 28 of the 40 dev pages.

| | Baseline | Sharpened |
| --- | --- | --- |
| Field accuracy (40 docs) | 89.4% | 89.2% |
| CER mean / median | 16.5% / 11.8% | 14.8% / 11.2% |
| Phone photos | 71.9% | 72.7% |
| Old paper | 100% | 95.5% |

CER improves (cleaner text overall, mostly stamps and footers), but field accuracy does
not: the differences are one or two fields either way. Off by default; enable with `LL_OCR_SHARPEN=1`.

## What would actually move the numbers

- **Phone photos** (weakest case) fail mostly at text *detection* on blurred, small text. The next thing to try is super-resolution or 2x upscaling of soft pages before detection, or a stronger detector.
- **Khatauni tables**: decimals and slashes lost inside table cells. Those are now flagged for review instead of trusted (see `validate.parse_area` and `parse_plot_id`).
- **Speed**: a CUDA GPU (about 1–2 s per page), or moving the project out of a OneDrive-synced folder. Sync traffic roughly doubled OCR time on the development laptop.
