# Evaluation — `multi` split (30 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 15.6% / 13.1% |
| Field accuracy (all fields) | 84.7% |
| Field accuracy (required fields) | 81.9% |
| Review rate | 80.0% |
| Straight-through accuracy (auto-accepted docs fully correct) | 83.3% |
| Fields flagged for a human (all extracted fields) | 19.6% |
| Precision of fields *not* flagged | 95.0% |
| Auto-accept threshold (calibrated on dev) | 0.88 |
| OCR time per document (CPU) | 16.4 s |
| Owner list exactly right (all documents) | 83.3% |
| Every co-owner found (multi-owner documents) | 4 of 6 |
| Parcel rows recovered (recall / precision) | 53.3% / 55.8% |
| Rows recovered in multi-row tables | 16 of 23 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 86.7% | 30 |
| father_name | 92.3% | 26 |
| khata_number | 83.3% | 30 |
| khasra_number | 66.7% | 30 |
| survey_number | 94.1% | 17 |
| plot_area | 56.7% | 30 |
| land_classification | 86.7% | 30 |
| village | 86.7% | 30 |
| tehsil | 96.7% | 30 |
| district | 96.7% | 30 |
| state | 96.7% | 30 |
| mutation_number | 82.6% | 23 |
| mutation_date | 78.3% | 23 |
| registration_number | 94.1% | 17 |
| registration_date | 76.5% | 17 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 93.3% | 12.9% |
| handwritten:True | 72.1% | 19.7% |
| profile:clean | 96.7% | 10.1% |
| profile:old | 90.6% | 15.9% |
| profile:photo | 69.2% | 26.7% |
| profile:scan | 80.7% | 13.9% |
| template:form_bilingual | 88.5% | 13.9% |
| template:khatauni_table | 75.2% | 19.4% |
| template:ror_english | 93.0% | 12.8% |
