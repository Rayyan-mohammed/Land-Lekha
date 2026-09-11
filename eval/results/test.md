# Evaluation — `test` split (40 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 15.7% / 11.1% |
| Field accuracy (all fields) | 84.8% |
| Field accuracy (required fields) | 84.3% |
| Review rate | 92.5% |
| Straight-through accuracy (auto-accepted docs fully correct) | 100.0% |
| Fields flagged for a human (all extracted fields) | 21.8% |
| Precision of fields *not* flagged | 96.2% |
| Auto-accept threshold (calibrated on dev) | 0.89 |
| OCR time per document (CPU) | 14.51 s |
| Owner list exactly right (all documents) | 85.0% |
| Every co-owner found (multi-owner documents) | 6 of 9 |
| Parcel rows recovered (recall / precision) | 58.1% / 61.0% |
| Rows recovered in multi-row tables | 16 of 32 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 90.0% | 40 |
| father_name | 83.3% | 36 |
| khata_number | 80.0% | 40 |
| khasra_number | 72.5% | 40 |
| survey_number | 69.2% | 26 |
| plot_area | 77.5% | 40 |
| land_classification | 92.5% | 40 |
| village | 85.0% | 40 |
| tehsil | 92.5% | 40 |
| district | 92.5% | 40 |
| state | 92.5% | 40 |
| mutation_number | 85.7% | 35 |
| mutation_date | 82.9% | 35 |
| registration_number | 87.0% | 23 |
| registration_date | 82.6% | 23 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 89.1% | 14.9% |
| handwritten:True | 67.7% | 18.5% |
| profile:clean | 97.2% | 10.1% |
| profile:old | 94.4% | 9.4% |
| profile:photo | 43.9% | 38.4% |
| profile:scan | 87.0% | 13.7% |
| template:form_bilingual | 75.3% | 18.2% |
| template:khatauni_table | 83.8% | 16.2% |
| template:ror_english | 94.6% | 12.4% |
