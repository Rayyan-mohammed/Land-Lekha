# Orientation recovery

Pages that read well upright, rotated and re-processed end to end. **18/18** rotated pages recovered to within 10 points of their upright field accuracy.

| Document | Template | Upright | 90° | 180° | 270° |
| --- | --- | --- | --- | --- | --- |
| dev-002 | ror_english | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |
| dev-003 | ror_english | 92% | 92% (rotate90+rotate180) | 92% (rotate180) | 92% (rotate90) |
| dev-004 | form_bilingual | 92% | 92% (rotate90+rotate180) | 92% (rotate180) | 92% (rotate90) |
| dev-008 | khatauni_table | 93% | 87% (rotate90+rotate180) | 87% (rotate180) | 93% (rotate90) |
| dev-012 | khatauni_table | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |
| dev-014 | form_bilingual | 100% | 100% (rotate90+rotate180) | 100% (rotate180) | 100% (rotate90) |

In brackets: the rotation steps the pipeline applied (`rotate90` from the text-line projection test, `rotate180` from the recognition-confidence check).
