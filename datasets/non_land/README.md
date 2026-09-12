# Non-land pages for the classification evaluation

Fourteen pages of the kinds an office receives by mistake, one folder per kind:

| Folder | Pages |
| --- | --- |
| `certificates/` | a school marksheet, a birth certificate |
| `invoices/` | a shop tax invoice (English), a shop bill (Hindi) |
| `bank/` | an account statement |
| `letters/` | an office letter |
| `handwritten_notes/` | a shopping list and lecture notes, in handwriting-style fonts, stained and tilted |
| `government_non_land/` | a vaccination certificate and a ration-card form - government seals, no land |
| `newspapers/` | a newspaper page |
| `photographs/` | a product label, a street photograph with no text, a blank page |

**Every page here is synthetic**, drawn by `datasets/build_non_land.py` from generic text with
no real person, account, document number or address. Nothing was downloaded. That keeps the
set free of anyone's personal documents, and it also means the set is small and tidy: it shows
the classifier's mechanism works, not that the job is finished. Real misfiled pages will be
messier, and the honest next step is a larger set drawn from public, licensed sources.

Beside each image is its OCR reading (`*.ocr.json`), produced by the same `run_ocr` an upload
goes through, so `eval/classify_eval.py` measures the classifier on what it would actually see.

Rebuild: `python datasets/build_non_land.py` (needs the OCR model; a few minutes on a CPU).
