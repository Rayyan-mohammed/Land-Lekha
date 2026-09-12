# Evaluation — `multi` split (30 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 15.8% / 13.5% |
| Field accuracy (all fields) | 84.2% |
| Field accuracy (required fields) | 82.4% |
| Review rate | 86.7% |
| Straight-through accuracy (auto-accepted docs fully correct) | 75.0% |
| Fields flagged for a human (all extracted fields) | 20.3% |
| Precision of fields *not* flagged | 94.0% |
| Auto-accept threshold (calibrated on dev) | 0.88 |
| OCR time per document (CPU) | 15.54 s |
| Owner list exactly right (all documents) | 76.7% |
| Every co-owner found (multi-owner documents) | 3 of 6 |
| Parcel rows recovered (recall / precision) | 55.6% / 58.1% |
| Rows recovered in multi-row tables | 16 of 23 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 83.3% | 30 |
| father_name | 88.5% | 26 |
| khata_number | 86.7% | 30 |
| khasra_number | 73.3% | 30 |
| survey_number | 94.1% | 17 |
| plot_area | 56.7% | 30 |
| land_classification | 93.3% | 30 |
| village | 86.7% | 30 |
| tehsil | 93.3% | 30 |
| district | 96.7% | 30 |
| state | 96.7% | 30 |
| mutation_number | 78.3% | 23 |
| mutation_date | 69.6% | 23 |
| registration_number | 94.1% | 17 |
| registration_date | 70.6% | 17 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 92.5% | 13.3% |
| handwritten:True | 71.9% | 19.5% |
| profile:clean | 96.7% | 10.2% |
| profile:old | 90.5% | 16.1% |
| profile:photo | 66.1% | 26.3% |
| profile:scan | 80.6% | 14.4% |
| template:form_bilingual | 86.2% | 14.1% |
| template:khatauni_table | 75.9% | 19.5% |
| template:ror_english | 93.0% | 13.0% |
