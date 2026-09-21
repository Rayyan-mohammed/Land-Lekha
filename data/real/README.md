# Real land records (for measuring, not for training)

Put real documents here to measure LandLekha on something other than generated data.

## Privacy first

* Only use documents you are allowed to use: public portal printouts (Bhulekh / Bhuiyan /
  Apna Khata), or team members' family records **with permission**.
* **Black out personal details you don't need** (Aadhaar numbers, phone numbers, addresses)
  before copying a file here. Names, khata/khasra numbers and places are what we measure.
* **Nothing in this folder except this README is ever committed.** The repository is public, and
  a land record carries real people's names. `.gitignore` enforces it: documents and their typed
  ground truth stay on the machine that measured them. Only the aggregate result is published,
  in `eval/results/real.md`, and it carries counts and field names - never a name or a value.

## Format: one image or PDF plus one JSON with the same name

```
data/real/
  up-bhulekh-01.jpg
  up-bhulekh-01.json
  mp-khasra-02.pdf
  mp-khasra-02.json
```

The JSON holds the **correct** values, typed by a person reading the document. Include only
the fields that are actually on the page:

```json
{
  "fields": {
    "owner_name": "राम प्रसाद शर्मा",
    "father_name": "मोहन लाल शर्मा",
    "khata_number": "00245",
    "khasra_number": "123/2",
    "plot_area": {"value": 0.412, "unit": "hectare"},
    "land_classification": "agricultural_irrigated",
    "village": "Rampur",
    "tehsil": "Sadar",
    "district": "Lucknow",
    "state": "Uttar Pradesh",
    "mutation_number": "4521",
    "mutation_date": "12/03/2019"
  }
}
```

* Names are written exactly as printed (Hindi stays Hindi).
* Places use the English name from `backend/extraction/master/gazetteer.json`.
* `land_classification` uses one of the keys in `backend/extraction/schema.py` (`LAND_CLASSES`).
* For several co-owners or khasra rows, also add `owners` / `parcels` lists in the shape shown
  in `docs/contracts.md`.
* Optional: a `"text"` field with the full page transcript enables the CER measurement.

## Measure

```bash
python eval/evaluate.py --split real --dir data/real
```

Results go to `eval/results/real.md`. Add a village that isn't in the gazetteer to the
gazetteer first, otherwise the place fields are (correctly) flagged as unknown.

## Measuring

```
python eval/real_eval.py
```

Scores every document here that has ground truth, with the same definition of a correct field
as the synthetic evaluation, so the two can be read side by side.

Record in each JSON who typed it (`"keyed_by"`). The honest target is two people typing the
same document independently and a third settling disagreements; until then say how many
readers there were, because one reader's slip becomes a false "wrong" in the score.
