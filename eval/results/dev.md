# Evaluation — `dev` split (40 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 15.3% / 12.1% |
| Field accuracy (all fields) | 87.0% |
| Field accuracy (required fields) | 87.1% |
| Review rate | 72.5% |
| Straight-through accuracy (auto-accepted docs fully correct) | 100.0% |
| Fields flagged for a human (all extracted fields) | 21.3% |
| Precision of fields *not* flagged | 96.6% |
| Auto-accept threshold (calibrated on dev) | 0.88 |
| OCR time per document (CPU) | 31.86 s |
| Owner list exactly right (all documents) | 82.5% |
| Every co-owner found (multi-owner documents) | 9 of 13 |
| Parcel rows recovered (recall / precision) | 60.8% / 61.6% |
| Rows recovered in multi-row tables | 30 of 51 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 90.0% | 40 |
| father_name | 83.8% | 37 |
| khata_number | 100.0% | 40 |
| khasra_number | 75.0% | 40 |
| survey_number | 86.2% | 29 |
| plot_area | 80.0% | 40 |
| land_classification | 87.5% | 40 |
| village | 85.0% | 40 |
| tehsil | 82.5% | 40 |
| district | 97.5% | 40 |
| state | 97.5% | 40 |
| mutation_number | 82.9% | 35 |
| mutation_date | 91.4% | 35 |
| registration_number | 77.3% | 22 |
| registration_date | 81.8% | 22 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 88.1% | 15.7% |
| handwritten:True | 82.8% | 12.6% |
| profile:clean | 95.6% | 9.9% |
| profile:old | 89.2% | 17.5% |
| profile:photo | 65.7% | 26.4% |
| profile:scan | 89.6% | 13.8% |
| template:form_bilingual | 88.0% | 12.8% |
| template:khatauni_table | 81.7% | 19.6% |
| template:ror_english | 97.3% | 9.7% |
