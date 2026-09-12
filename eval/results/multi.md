# Evaluation — `multi` split (30 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 15.5% / 13.1% |
| Field accuracy (all fields) | 85.2% |
| Field accuracy (required fields) | 83.8% |
| Review rate | 63.3% |
| Straight-through accuracy (auto-accepted docs fully correct) | 54.5% |
| Fields flagged for a human (all extracted fields) | 9.8% |
| Precision of fields *not* flagged | 92.3% |
| Auto-accept threshold (calibrated on dev) | 0.81 |
| OCR time per document (CPU) | 19.4 s |
| Owner list exactly right (all documents) | 83.3% |
| Every co-owner found (multi-owner documents) | 4 of 6 |
| Parcel rows recovered (recall / precision) | 53.3% / 55.8% |
| Rows recovered in multi-row tables | 16 of 23 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 86.7% | 30 |
| father_name | 92.3% | 26 |
| khata_number | 86.7% | 30 |
| khasra_number | 76.7% | 30 |
| survey_number | 94.1% | 17 |
| plot_area | 56.7% | 30 |
| land_classification | 86.7% | 30 |
| village | 86.7% | 30 |
| tehsil | 96.7% | 30 |
| district | 96.7% | 30 |
| state | 96.7% | 30 |
| mutation_number | 78.3% | 23 |
| mutation_date | 73.9% | 23 |
| registration_number | 94.1% | 17 |
| registration_date | 76.5% | 17 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 93.7% | 12.9% |
| handwritten:True | 72.7% | 19.5% |
| profile:clean | 97.9% | 10.1% |
| profile:old | 90.3% | 15.8% |
| profile:photo | 69.2% | 26.8% |
| profile:scan | 81.3% | 13.8% |
| template:form_bilingual | 89.1% | 13.6% |
| template:khatauni_table | 75.8% | 19.4% |
| template:ror_english | 93.0% | 12.8% |
