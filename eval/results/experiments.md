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

Cost, measured end to end on this laptop: a blurred phone photo goes from about 70 s to about
145 s, because the page is read twice. Pages that read well are unaffected. The upload screen
says so ("a blurred page is read twice and takes longer") and the review screen marks such a page
`read twice`. If the wait matters more than the last point of accuracy at a busy counter, set
`LL_OCR_RETRY_SOFT=0`.

## 12. Reading numbers again, in English alone — adopted

After the second read, 40 of the 70 fields still wrong on dev (57%) were numeric: khasra, survey,
mutation and registration numbers, areas and dates. These are the fields a record is looked up by,
so they are the worst ones to get wrong. The cause is not resolution — it is the alphabet. The
Hindi+English model may answer with Devanagari digits or with letters shaped like digits, and on a
*clean* page it does:

| Field | Truth | Hindi+English | English only |
| --- | --- | --- | --- |
| survey_number | 190/4 | `/q०/4` (0.21) | **190/4** (0.87) |
| registration_number | 1996/40440 | `/११6/५०५५०` (0.28) | **1996/40440** (0.62) |
| plot_area | 3.598 | `3.५१४ हेक्टेयर` (0.44) | `3.598 ZaZT` (0.54) |
| khata_number | 00806 | **00806** (0.97) | `00306` (0.94) |

The last row is the warning: where the main model is sure, the English reader is worse. So it is
only asked about tokens read under 0.5, and its answer is kept only if it is 0.15 more confident
and comes back as a number. Tokens with a Devanagari letter in them are never offered, because
the English model cannot write one back (`1124/6क` would lose its क).

**What the gate had to learn.** The first version offered it every unsure number-shaped token.
That fixed four fields and broke two — both dates the main model had already read correctly *in
Devanagari digits*:

| Page | Hindi+English | English only | Truth |
| --- | --- | --- | --- |
| dev-022 | `०२/०३/२००२` (0.44) | `03/03/3002` (0.88) | 02/03/2002 |
| dev-035 | `०२\|०९/२०१९` (0.37) | `02/08/3098` (0.53) | 02/09/2019 |

Extraction reads Devanagari digits, so those tokens were already right; a model with no Devanagari
can only transliterate them by shape, and it guesses. The rule that follows is simple: **a number
written entirely in Devanagari digits is left alone**. What is worth a second look is a number in
Latin digits, or one holding a letter no number can contain (the `S` of `S४५`, the `q` of `/q०/4`).
Mixed scripts count as Latin — `/११6/५०५५०` mixes them and is a bad read.

| Gate (both at the threshold of the day, 0.88) | Fields fixed | Fields broken | Precision of unflagged |
| --- | --- | --- | --- |
| every unsure number-shaped token | 4 | 2 | 96.4% |
| Devanagari-only numbers left alone | **3** | **0** | **96.5%** |

**Holding back the confidence.** A wrong re-read can be confident: `S४५` (0.25) becomes `534`
(0.90) when the truth is 584. Keeping the text but recording the *old* confidence was tried, so
that such a field stays flagged. It changes nothing measurable — the confidence model is refitted
either way, and dev came out at 87.6% accuracy, 95.5% precision on unflagged fields for both. The
simpler version is kept (`eval/results/exp-dev-numbers-capped.md`).

**Where the threshold goes, and a fix to how it is picked.** Refitting the confidence model on the
new readings moved the calibrated threshold from 0.88 to 0.81, which on dev looked like a bargain:
11.1% of fields flagged at 95.5% precision. On the held-out split it was not. The calibrator takes
the *lowest* threshold whose out-of-fold precision meets the 95% target, and here that range is
wide and flat - 95.1% at 0.81, 95.4% at 0.88, 95.5% at 0.91 - so the lowest point is the one with
no margin, and held-out precision came out at 94.4%:

| Held-out test, same readings | 0.81 | 0.88 | 0.90 |
| --- | --- | --- | --- |
| Fields flagged for a person | 7.5% | 11.9% | 15.3% |
| Precision of unflagged fields | 94.4% | 95.4% | **96.4%** |
| Auto-accepted documents | 27 | 19 | 13 |

`eval/calibrate.py` now takes the middle of that range instead of its lower edge, which is 0.90
here. The same rule on the previous readings gives 0.93, so it is consistently more careful, not
tuned to this experiment.

With the model refitted and the threshold at 0.90:

| Dev split | Before (0.88) | After (0.90) |
| --- | --- | --- |
| Field accuracy | 87.0% | **87.6%** |
| Required-field accuracy | 87.1% | **87.5%** |
| Fields flagged for a person | 21.3% | 21.3% |
| Precision of unflagged fields | 96.6% | 96.4% |
| Documents needing a human | 72.5% | 75.0% |

On the held-out test split, run after the dev decision:

| Held-out test | Before | After |
| --- | --- | --- |
| Field accuracy | 86.8% | **88.1%** |
| Required-field accuracy | 86.4% | **87.5%** |
| Fields flagged for a person | 15.7% | **15.3%** |
| Precision of unflagged fields | 96.4% | 96.4% |
| Documents needing a human | 70.0% | **67.5%** |
| Handwritten entries | 72.8% | **77.4%** |

Field by field on that split, only numbers moved at all, which is what the change was aimed at:

| Field | Before | After |
| --- | --- | --- |
| survey_number | 73.1% | **80.8%** |
| mutation_date | 80.0% | **85.7%** |
| khata_number | 82.5% | **87.5%** |
| mutation_number | 85.7% | **88.6%** |
| khasra_number | 75.0% | **77.5%** |
| registration_number | 95.7% | 91.3% |

Every other field is unchanged to the decimal. Registration numbers are the one loss - 4.4 points
over 23 documents is a single document - and they remain the best-read number of the set.

Two other things went backwards and are worth saying plainly. Auto-accepted documents with every
required field right went from 11 of 12 to 11 of 13: thirteen documents now clear without a person
instead of twelve, and the extra one carries a wrong field. And dev precision slipped from 96.6%
to 96.4%. Precision over fields on the held-out split - the number a verifier actually feels - is
unchanged at 96.4%.

The multi-owner split, which is the hardest of the three, moved both ways:

| Multi-owner split (30 documents) | Before (0.88) | After (0.90) |
| --- | --- | --- |
| Field accuracy | 84.7% | **85.2%** |
| Parcel rows recovered | 53.3% | **55.6%** |
| Fields flagged for a person | 19.6% | 20.8% |
| Precision of unflagged fields | 95.0% | 94.3% |
| Every co-owner found | 4 of 6 | 3 of 6 |

The co-owner count is all-or-nothing over six documents, so one changed name moves it; it moved
the same way when the second read was adopted and moved back after. Unflagged precision on this
split has never reached the other two, which is the honest reason to keep the multi-owner Khatauni
in front of a verifier.

Cost: one extra recognition per unsure number. Across 220 pages the worst page offers six tokens
and the median offers one, and each is a small crop, so this is not the expensive part of a read.
The English model is loaded on first use, so a run with no unsure numbers never pays for it.
`LL_OCR_NUMBER_PASS=0` turns it off.

## What would actually move the numbers

- **Phone photos:** a recognition model trained on blurred/phone-captured Devanagari (fine-tuning on real field photos), or a stronger OCR engine. Until then, the quality check asks for a retake.
- **Khatauni tables:** the decimals and slashes that the recogniser loses are flagged for review rather than trusted (`validate.parse_area`, `parse_plot_id`).
- **Multi-row Khatauni tables:** some documents lose a whole column of parcel rows although OCR read every value. On dev-004 and multi-019 every khasra number is read exactly (`704/4`, `329/9`, `1268`, `1340`) and parses, yet the rows come out with no khasra; on test-033 and multi-010 the same happens to the area column. The fix is in the table-column assignment (`extractor.py`, parcel rows), not in OCR. Rows after the first also carry no confidence of their own, so a wrong second row cannot be flagged yet.
- **What is left in the two weakest fields** (both 77.5% on the held-out split, counted one by one
  after the english-only number pass). `khasra_number`: 3 not found at all, 3 confident single-digit
  misreads by the main model (`1805/1` read as `1305/1` at 0.95 - nothing to re-read, the model is
  sure), one Devanagari suffix read as a quote (`273/6ग` as `273/6"`), one separator never detected
  (`१२६३ ९क`, a space where the slash is). `plot_area`: 4 not found, 2 Devanagari digit misreads
  inside an otherwise clean number (`३.०३७` for 3.087), one lost decimal point read at 0.98
  confidence (`257` for 2.57), one number glued to its unit word (`I3.SI बीघा`). So the remaining
  loss is roughly half labelling and half a recogniser that is confidently wrong; neither responds
  to reading the page again.
- **Two extraction rules worth trying** (they are cheap and both showed up above): a space between
  two number groups in a khasra is almost always a slash, and an area of `257 bigha` where the
  neighbouring rows are single digits has lost its decimal point. Both are safer as flags than as
  silent corrections.
- **Speed:** a CUDA GPU (about 1–2 s per page), born-digital PDFs (0.5 s, adopted), and keeping the project out of OneDrive-synced folders. Sync traffic roughly doubled OCR time on the development laptop.
