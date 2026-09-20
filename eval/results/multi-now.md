# Evaluation — `multi` split (30 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 15.7% / 13.3% |
| Field accuracy (all fields) | 85.2% |
| Field accuracy (required fields) | 83.8% |
| Review rate | 86.7% |
| Straight-through accuracy (auto-accepted docs fully correct) | 50.0% |
| Fields flagged for a human (all extracted fields) | 20.8% |
| Precision of fields *not* flagged | 94.3% |
| Auto-accept threshold (calibrated on dev) | 0.9 |
| OCR time per document (CPU) | 29.82 s |
| Owner list exactly right (all documents) | 76.7% |
| Every co-owner found (multi-owner documents) | 3 of 6 |
| Parcel rows recovered (recall / precision) | 55.6% / 58.1% |
| Rows recovered in multi-row tables | 16 of 23 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 83.3% | 30 |
| father_name | 88.5% | 26 |
| khata_number | 90.0% | 30 |
| khasra_number | 80.0% | 30 |
| survey_number | 94.1% | 17 |
| plot_area | 56.7% | 30 |
| land_classification | 93.3% | 30 |
| village | 86.7% | 30 |
| tehsil | 93.3% | 30 |
| district | 96.7% | 30 |
| state | 96.7% | 30 |
| mutation_number | 78.3% | 23 |
| mutation_date | 73.9% | 23 |
| registration_number | 94.1% | 17 |
| registration_date | 70.6% | 17 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 92.5% | 13.3% |
| handwritten:True | 74.5% | 19.3% |
| profile:clean | 97.9% | 10.1% |
| profile:old | 91.5% | 16.0% |
| profile:photo | 66.1% | 26.3% |
| profile:scan | 82.1% | 14.2% |
| template:form_bilingual | 89.1% | 13.8% |
| template:khatauni_table | 75.9% | 19.5% |
| template:ror_english | 93.0% | 13.0% |
