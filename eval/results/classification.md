# Land-document classification

110 land pages (real OCR readings of the dev, test and multi splits) and 14 non-land pages
(`datasets/non_land/`, synthetic, no real person's document), classified from their OCR text exactly as
`processing.py` does it. A page the quality check calls unreadable is *undetermined*: it goes back for a
retake with no fields, and is not counted as a decision either way.

| Metric | Value |
| --- | --- |
| Accuracy (decided pages) | **100.0%** (115 of 115) |
| Precision - of pages called land, how many are | **100.0%** |
| Recall - of land pages, how many were kept | **100.0%** |
| F1 | **1.000** |
| Undetermined (unreadable, sent for retake) | 9 |

Confusion matrix (rows: truth, columns: verdict):

| | called land | called not land |
| --- | --- | --- |
| land page | 105 | 0 |
| not a land page | 0 | 10 |

## By kind of page

| Kind | pages | called land | called not land | undetermined |
| --- | --- | --- | --- | --- |
| land/clean | 25 | 25 | 0 | 0 |
| land/old | 20 | 20 | 0 | 0 |
| land/photo | 17 | 12 | 0 | 5 |
| land/scan | 48 | 48 | 0 | 0 |
| non_land/bank | 1 | 0 | 1 | 0 |
| non_land/certificates | 2 | 0 | 2 | 0 |
| non_land/government_non_land | 2 | 0 | 2 | 0 |
| non_land/handwritten_notes | 2 | 0 | 2 | 0 |
| non_land/invoices | 2 | 0 | 1 | 1 |
| non_land/letters | 1 | 0 | 1 | 0 |
| non_land/newspapers | 1 | 0 | 1 | 0 |
| non_land/photographs | 3 | 0 | 0 | 3 |

## Document types named on the land pages

| Type | pages |
| --- | --- |
| unknown | 33 |
| khatiyan | 19 |
| jamabandi | 19 |
| khatauni | 17 |
| particulars_form | 16 |
| record_of_rights | 1 |

## Undetermined pages

- land/photo / dev-009: too little was read from this page to say what it is
- land/photo / dev-030: too little was read from this page to say what it is
- land/photo / test-001: too little was read from this page to say what it is
- land/photo / test-022: too little was read from this page to say what it is
- land/photo / multi-014: too little was read from this page to say what it is
- non_land/invoices / hindi_bill: too little was read from this page to say what it is
- non_land/photographs / blank_page: too little was read from this page to say what it is
- non_land/photographs / product_label: too little was read from this page to say what it is
- non_land/photographs / street_photo: too little was read from this page to say what it is

## Mistakes

None on this data.

The non-land set is small and synthetic; it shows the mechanism works, not that it is finished.
Reproduce: `python eval/classify_eval.py`. The classifier is a rule ensemble over kinds of
evidence (`backend/classify/land.py`); the numbers above are its own decisions, not a fit.
