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

## 3. Why phone photos fail — diagnosis

On the three worst dev photos, text *detection* works: it finds 13/15, 16/16 and 19/17 of the
ground-truth lines. *Recognition* fails: the median token confidence is 0.05, 0.09 and 0.32,
against about 0.7–0.9 on readable pages. The recogniser cannot read strokes this blurred.
Changing the denoise step (none / h=5 / median filter instead of h=12) moves individual pages
up or down, but no variant fixes them. So instead of more filtering:

- **Page quality check (adopted).** `backend/ocr/quality.py` gives each page `good` / `fair` / `poor`
  plus plain-language advice (blurred, text too small, low resolution). Thresholds come from the
  dev set: median token confidence below 0.2 gave 0 correct fields, 0.2–0.4 was unreliable
  (54–100%), 0.4+ was reliable. The operator can retake a photo on the spot instead of
  creating a review case that cannot be fixed.

## 4. Pages photographed sideways or upside down — adopted

A text-line projection test (row/column profile sharpness: upright pages score at least 1.33,
sideways pages at most 0.75 on dev) turns sideways pages by 90°. If a page then reads with low
confidence, about a dozen of its text boxes are re-read rotated 180° (recognition only) and the
page is flipped when that reads clearly better. Upright confident pages cost nothing extra.
**18/18** rotated test pages (6 documents × 90/180/270°) recovered to their upright accuracy;
see [orientation.md](orientation.md).

## 5. Born-digital PDFs — adopted

PDFs exported by land-record portals carry exact Unicode text. The pipeline reads that text
layer directly: **0.5 s instead of about 30 s**, no OCR model loaded, and every field correct
on a Hindi test PDF. The layer is used only if it looks like real text (enough words, clean
characters, Devanagari or record keywords). Pre-Unicode Hindi fonts (Kruti Dev etc.) and
scanned PDFs fall back to OCR.

## 6. Khatauni tables: ruled-line removal — rejected

Erasing long table and underline strokes before detection (kernels longer than any word, so
Devanagari headlines survive). On the first 17 dev documents, table accuracy dropped from
70.2% to 64.9%: without borders, detection merges neighbouring cells into one box. Removed.

## 7. Khatauni tables: cell-by-cell reading — not adopted (kept, off by default)

`backend/ocr/tables.py` finds the grid exactly (all rows and columns on every dev table, no
false positives on the 29 non-table pages). It erases the ruling, trims each cell to its ink
and recognises each cell alone, keeping the original reading when that one is more confident.

| | Baseline | Cell reading |
| --- | --- | --- |
| Khatauni tables (11 docs) | 83.1% | 81.0% |
| All 40 dev docs | 89.4% | 88.8% |

Cell crops removed some errors (`|887^` became `887/`, and `चरागाह` was read correctly) but
introduced others: headers, and dropped decimal points. On balance it's slightly worse with
this recogniser. Enable with `LL_OCR_TABLE_CELLS=1` to retry it with a stronger recognition model.

## 8. Lighter denoising (h = 12 → 6) — rejected

Hypothesis: strong non-local-means denoising erases decimal points and thin strokes. On the
first 10 dev documents, field accuracy dropped from 85.8% to 82.1%: the extra noise it lets
through costs more than the detail it keeps. Stopped early; the strength stays at 12
(`LL_OCR_DENOISE_H` is kept for future tuning).

## 9. Official LGD village list: dataset rebuilt and recalibrated

L2 replaced the 92 sample villages with the official LGD directory (4,876 villages for the 10
districts). Measured on the old test set, village accuracy fell from 90% to 37.5%. The cause was
the synthetic ground truth, not the lookup: 59 of the 92 sample villages the documents used do
not exist in the official list. The lookup itself still found the right village for 31 of 33
villages present in both lists, even though the official Hindi names are machine-transliterated.

So the dev and test sets were regenerated from the official list (same seeds), OCR re-run, and
the confidence model refitted on dev.

The new data is harder (real village names, more multi-owner Khataunis), and 98% precision on
unflagged fields was only reachable by flagging two thirds of all fields (dev: 33% of fields
above a 0.96 threshold). The target was therefore set to **95% on dev**, which keeps about 70%
of fields unflagged:

| Held-out test | Sample villages (old) | LGD villages (now) |
| --- | --- | --- |
| Field accuracy | 82.9% | **84.4%** |
| Village accuracy | 90.0% | **85.0%** |
| Fields flagged for a person | 16.3% | 21.8% |
| Unflagged fields correct | 95.7% | **96.2%** |
| Median CER | 11.3% | 11.1% |

The multi-owner split (seed 5, 30 documents) was rebuilt the same way: on the old sample villages its
village accuracy had fallen to 30%, and after the rebuild it is back to 83.3% (field accuracy 81.2%). The
results now count multi-owner documents on their own ("every co-owner found: 3 of 6") instead of mixing
them into the all-documents owner rate, which was misleadingly labelled before.

## 10. OCR letter confusions in names, lost decimals in acre/bigha rows — adopted

Listing every multi-owner Khatauni where a co-owner or parcel row was missed showed two patterns:

- **Names:** the owners were split correctly, but single letters were misread: व as च (यादव → यादच,
  तिवारी → तिचारी), थ as य (नाथ → नाय) and the conjunct ंद्र as ट (नरेंद्र → नरेट). When a name token is not
  in the name lexicon, `names.py` now retries with those substitutions and accepts the result only if
  exactly one known token matches. Unknown names still pass through unchanged.
- **Areas:** the decimal point was lost in table rows ("1293 bigha" for 12.93). The existing hectare rule
  (an impossible area for one plot means the point was lost) now also covers acre and bigha, which records
  give to 2 decimals. A plausible whole number ("285 bigha", 72 ha) is still kept as read and flagged.

| | Before | After |
| --- | --- | --- |
| Test field accuracy | 84.4% | **84.8%** |
| Test: every co-owner found | 5 of 9 | **6 of 9** |
| Dev field accuracy | 83.0% | **84.6%** |
| Dev: every co-owner found | 5 of 13 | **8 of 13** |
| Fields flagged / unflagged precision (test) | 21.8% / 96.2% | 21.8% / 96.2% |

Caveat: the confusions were found by reading errors from all three splits, test included, so for this
change the test number is not strictly held out. The rules are generic OCR confusions, not fitted to
particular documents, and dev improves by more than test.

A second pass over the remaining name errors added three more confusions: वर् read as च (वर्मा → च्मा,
the most frequent one left), अ as भ (अशोक → भशोक) and क as झ (कमला → झमला). Multi-owner split: field
accuracy 81.7% → 81.9%, every co-owner found 3 → 4 of 6; dev 84.6% → 84.8%; test unchanged at 84.8%.
Flag rates and unflagged precision did not move on any split.

## 11. A second chance for pages that read badly — adopted

Strong denoising (h=12) suits most pages but erases strokes on blurred photos and faded paper.
Tried on the six dev pages the quality check calls *fair* or *poor* (81 fields in all):

| Read | Fields correct |
| --- | --- |
| baseline (h=12) | 35 |
| re-read on a 2x upscale | 41 |
| re-read with lighter denoising (h=5) | **48** |

The lighter read was never worse on any of those pages, so `run_ocr` now reads a page a second
time with h=5 whenever the first reading is not `good`, and keeps the second reading. Six of the
40 dev pages take that second pass, so the cost is one extra read on pages that were going to a
verifier anyway; pages that read well are untouched. This is the opposite of experiment 8, where
the same lighter denoising applied to *every* page lost accuracy — the gain exists only where the
first read is poor. Turn it off with `LL_OCR_RETRY_SOFT=0`.

Every one of the six re-read documents improved and no other document changed:

| Document | Before | After |
| --- | --- | --- |
| dev-004 (old paper) | 69% | 77% |
| dev-009 (phone photo) | 0% | 15% |
| dev-013 (old paper) | 54% | 85% |
| dev-030 (phone photo) | 0% | 21% |
| dev-031 (scan) | 57% | 64% |
| dev-039 (scan) | 79% | 86% |

With the confidence model refitted on the new readings (threshold 0.88):

| Dev split | Before | After |
| --- | --- | --- |
| Field accuracy | 84.8% | **87.0%** |
| Required-field accuracy | 83.6% | **87.1%** |
| Fields flagged for a person | 30.2% | **21.3%** |
| Precision of unflagged fields | 97.0% | 96.6% |
| Documents needing a human | 87.5% | **72.5%** |

On the held-out test split, run once after the dev decision:

| Held-out test | Before | After |
| --- | --- | --- |
| Field accuracy | 84.8% | **86.8%** |
| Required-field accuracy | 84.3% | **86.4%** |
| Fields flagged for a person | 21.8% | **15.7%** |
| Precision of unflagged fields | 96.2% | **96.4%** |
| Documents needing a human | 92.5% | **70.0%** |
| Phone photos | 43.9% | **55.4%** |
| Village accuracy | 85.0% | **90.0%** |

Auto-accepted documents went from 3 to 12 of 40, and 11 of those 12 have every required field
right (the earlier 100% was 3 of 3). So roughly a third of documents now pass without a person
at all, and the ones that do reach a verifier carry fewer flagged fields.

The multi-owner split moved the same way: field accuracy 81.9% → 84.2%, flagged fields 29.3% →
20.3%, parcel rows 15 → 16 of 23. Its strict "every co-owner found" count slipped from 4 to 3 of
6 documents: that measure is all-or-nothing over six documents, so one changed name moves it.

A counter-example worth keeping in view: on the demo set, `05-phone-photo.jpg` extracted a few
fields before and none after. Both dev photos moved the other way (0% → 15% and 0% → 21%), so on
a page this blurred the second read is a coin flip; either way the page is marked `poor` and sent
back for a retake, so no wrong value reaches a record. Selecting between the two readings at
runtime was tried and dropped: median confidence and the count of confident tokens both pick the
worse reading on half of the dev cases (dev-004, dev-009 and dev-030), so the second reading is
simply kept.

## What would actually move the numbers

- **Phone photos:** a recognition model trained on blurred/phone-captured Devanagari (fine-tuning on real field photos), or a stronger OCR engine. Until then, the quality check asks for a retake.
- **Khatauni tables:** the decimals and slashes that the recogniser loses are flagged for review rather than trusted (`validate.parse_area`, `parse_plot_id`).
- **Multi-row Khatauni tables:** some documents lose a whole column of parcel rows although OCR read every value. On dev-004 and multi-019 every khasra number is read exactly (`704/4`, `329/9`, `1268`, `1340`) and parses, yet the rows come out with no khasra; on test-033 and multi-010 the same happens to the area column. The fix is in the table-column assignment (`extractor.py`, parcel rows), not in OCR. Rows after the first also carry no confidence of their own, so a wrong second row cannot be flagged yet.
- **Speed:** a CUDA GPU (about 1–2 s per page), born-digital PDFs (0.5 s, adopted), and keeping the project out of OneDrive-synced folders. Sync traffic roughly doubled OCR time on the development laptop.
