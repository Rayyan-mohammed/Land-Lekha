# Orientation recovery

Pages that read well upright (≥90% of fields, at most two per template), rotated and re-processed end to end.
**18/18** rotated pages recovered to within 10 points of their upright field accuracy — in this run every one of them
matched its upright accuracy exactly. `dev-010` is a phone-photo page, so the recovery is not limited to flat scans.

| Document | Template | Upright | 90° | 180° | 270° |
| --- | --- | --- | --- | --- | --- |
| dev-001 | khatauni_table | 92% | 92% (rotate90+rotate180) | 92% (rotate180) | 92% (rotate90) |
| dev-003 | ror_english | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |
| dev-005 | khatauni_table | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |
| dev-007 | form_bilingual | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |
| dev-010 | form_bilingual | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |
| dev-015 | ror_english | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |

In brackets: the rotation steps the pipeline applied (`rotate90` from the text-line projection test, `rotate180` from the recognition-confidence check).
Re-run after the second read was added, so the sample is drawn from the current OCR cache and differs from earlier versions of this table.
