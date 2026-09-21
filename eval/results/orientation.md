# Orientation recovery

Pages that read well upright (≥90% of fields, at most two per template), rotated and re-processed end
to end. **18/18** rotated pages recovered to within 10 points of their upright field accuracy; `dev-001`
lost one field at 90° and 180° (92% against 100% upright), the rest matched exactly. `dev-010` is a
phone-photo page, so the recovery is not limited to flat scans.

**A proposed 90° turn is now confirmed before it is kept.** The projection test decides from the shape
of the ink, and a real Haryana deed printed upright - a two-column form - scored inside the band
sideways pages occupy and was turned on its side. The page is now also read the way it arrived, and
whichever reading is made of words wins (`backend/ocr/pipeline.py`, `confirm_rotate90`). Recognition
confidence could not decide it: on that deed the correct upright text scored lower than the sideways
noise. None of the 18 genuinely rotated pages above had its turn undone; the deed now is.

| Document | Template | Upright | 90° | 180° | 270° |
| --- | --- | --- | --- | --- | --- |
| dev-001 | khatauni_table | 100% | 92% (rotate90+rotate180) | 92% (rotate180) | 100% (rotate90) |
| dev-003 | ror_english | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |
| dev-005 | khatauni_table | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |
| dev-007 | form_bilingual | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |
| dev-010 | form_bilingual | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |
| dev-015 | ror_english | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |

In brackets: the rotation steps the pipeline applied (`rotate90` from the text-line projection test, `rotate180` from the recognition-confidence check).
