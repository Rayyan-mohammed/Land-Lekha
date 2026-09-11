# Evaluation — `multi` split (30 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 16.7% / 13.5% |
| Field accuracy (all fields) | 81.9% |
| Field accuracy (required fields) | 79.5% |
| Review rate | 96.7% |
| Straight-through accuracy (auto-accepted docs fully correct) | 100.0% |
| Fields flagged for a human (all extracted fields) | 29.3% |
| Precision of fields *not* flagged | 94.7% |
| Auto-accept threshold (calibrated on dev) | 0.89 |
| OCR time per document (CPU) | 14.16 s |
| Owner list exactly right (all documents) | 80.0% |
| Every co-owner found (multi-owner documents) | 4 of 6 |
| Parcel rows recovered (recall / precision) | 53.3% / 55.8% |
| Rows recovered in multi-row tables | 15 of 23 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 83.3% | 30 |
| father_name | 84.6% | 26 |
| khata_number | 83.3% | 30 |
| khasra_number | 70.0% | 30 |
| survey_number | 94.1% | 17 |
| plot_area | 53.3% | 30 |
| land_classification | 93.3% | 30 |
| village | 83.3% | 30 |
| tehsil | 93.3% | 30 |
| district | 90.0% | 30 |
| state | 93.3% | 30 |
| mutation_number | 78.3% | 23 |
| mutation_date | 69.6% | 23 |
| registration_number | 88.2% | 17 |
| registration_date | 70.6% | 17 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 88.6% | 15.0% |
| handwritten:True | 71.9% | 19.0% |
| profile:clean | 96.7% | 10.2% |
| profile:old | 84.4% | 18.1% |
| profile:photo | 62.4% | 28.0% |
| profile:scan | 79.8% | 14.7% |
| template:form_bilingual | 86.2% | 14.1% |
| template:khatauni_table | 71.3% | 20.5% |
| template:ror_english | 90.7% | 14.8% |
