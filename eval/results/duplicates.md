# Finding the same parcel twice

The upload check catches a file uploaded twice by its hash. The case that matters is different:
the same parcel arriving again as a **different photograph**, read slightly differently. This
measures that.

Reproduce: `python eval/duplicates_eval.py --split test`

## How it is measured

Each document's ground truth stands in for the record already in the register. What the
pipeline actually extracted from the page - OCR errors and all - stands in for the record
arriving now.

* **Positive**: the extracted record against its own ground truth. Must be found.
* **Negative**: the same extracted record against all 39 other documents. Must not be found.

## Result on the held-out test split

| | |
| --- | --- |
| The same parcel, read again | **32 of 40 found — 80.0%** |
| Different parcels | **0 false matches in 1,560 comparisons** |

Nothing was wrongly joined. That is the side of this trade-off that matters: a false duplicate
would block a genuine record from being registered, and a missed one only means the second copy
goes to a verifier like any other document.

## Why the eight were missed

Not one of them is a scoring problem. In every case the page did not give up the fields the
lookup needs:

| Document | What happened |
| --- | --- |
| test-001 | village read as `hu`, no khasra, no district - a phone photo the quality check rejected |
| test-021 | no village read |
| test-037, test-039 | no khasra read |
| test-022 | village read as `Vella` instead of `Titoriya` |
| test-036 | village read as `Pindara` instead of `Chitaura` |
| test-002, test-019 | all fields present, but the values differ too much to match |

So duplicate detection is bounded by extraction, not by its own rules. Six of the eight would
be found if the village or the khasra had been read at all.

## What the near match buys

Exact khasra matching alone would have missed the parcels whose number came back one character
out - measured misreadings from this very split: `1805/1` as `1305/1`, `1501/4` as `501/4`,
`1263/9क` as `12639क`, `273/6ग` as `273/6`. A near match scores lower than an exact one
(0.45 against 0.6), so a near khasra on its own cannot reach the threshold: the khata or the
owner has to agree as well. And a different village is never a duplicate, whatever the numbers
look like.
