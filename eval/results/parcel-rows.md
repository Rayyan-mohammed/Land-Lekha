# Why parcel rows score 55.6%, and what that number means

A Khatauni lists several khasra rows under one khata. "Parcel rows recovered" is the strictest
metric in this repository, and the low figure has been misread inside the team as *rows going
missing*. It is not that. This is what is actually happening, measured over 181 ground-truth
rows across the dev, test and multi splits.

## The metric is all-or-nothing

A row counts as recovered only when **all four** of khasra number, area value, area unit and
land class are exactly right (`eval/evaluate.py`, `parcel_rows`). One wrong character in any
one of them discards the whole row.

**110 of 181 rows are fully correct — 60.8%.** Of the 71 that are not:

| What was wrong in the row | Rows |
| --- | --- |
| area value | 47 |
| khasra number | 40 |
| land class | 25 |
| area unit | 23 |

(A row can fail on more than one, and 13 of them fail on all four - those are pages that read
badly as a whole, not row-alignment problems.)

## Rows are not being lost

Row *alignment* works. Across the multi split only two ground-truth rows had no predicted row
at all, both on `multi-014` - a handwritten phone photo that scored 0% on every field and was
correctly sent back by the quality check. Every other document produced exactly as many rows
as the page has, in the right order. An earlier note in the project claimed whole columns were
being dropped; that is no longer true and the check above is how to confirm it.

## The orchard problem

`बाग` (orchard) is three characters in a narrow table cell, and it is the single most
frequently lost land class. What the recogniser actually returns for it:

| Document | Read as |
| --- | --- |
| dev-013 | `dाम` |
| test-034 | `ँम` |
| dev-026 | nothing |
| test-029 | `बार` |

This is a recogniser limit on very short words in table cells, not a missing alias - the word
is in the vocabulary and the extractor would match it if it were read. Adding fuzzy matching
here was considered and rejected: `बार` is one character from `बाग`, and guessing would put a
confident wrong land class on a parcel.

## What changed

Rows now carry their own confidence - the weakest cell in the row - and anything below the
trust threshold is flagged as rule `ROW-1`, naming the row number and the cell that failed:

```
consistency failed: ROW-1 (row 2: khasra_number at 0.05)
consistency failed: ROW-1 (row 3: land_classification at 0.03)
```

Before this, only the first row was mirrored into the flat fields, so a wrong value in the
second row of a table had nothing to flag it and was shown to a verifier with no indication
that it was uncertain. The confidence model already knew - the misread row above scores 0.05 -
there was simply no way to act on it.

Row accuracy is unchanged by this; the point is that a wrong row can no longer pass silently.
