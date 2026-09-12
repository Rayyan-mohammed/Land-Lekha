# Evaluation — `dev` split (40 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 15.2% / 12.3% |
| Field accuracy (all fields) | 87.4% |
| Field accuracy (required fields) | 87.5% |
| Review rate | 70.0% |
| Straight-through accuracy (auto-accepted docs fully correct) | 100.0% |
| Fields flagged for a human (all extracted fields) | 19.8% |
| Precision of fields *not* flagged | 96.4% |
| Auto-accept threshold (calibrated on dev) | 0.88 |
| OCR time per document (CPU) | 60.76 s |
| Owner list exactly right (all documents) | 82.5% |
| Every co-owner found (multi-owner documents) | 9 of 13 |
| Parcel rows recovered (recall / precision) | 62.2% / 63.0% |
| Rows recovered in multi-row tables | 30 of 51 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 90.0% | 40 |
| father_name | 83.8% | 37 |
| khata_number | 100.0% | 40 |
| khasra_number | 77.5% | 40 |
| survey_number | 89.7% | 29 |
| plot_area | 80.0% | 40 |
| land_classification | 87.5% | 40 |
| village | 85.0% | 40 |
| tehsil | 82.5% | 40 |
| district | 97.5% | 40 |
| state | 97.5% | 40 |
| mutation_number | 85.7% | 35 |
| mutation_date | 91.4% | 35 |
| registration_number | 81.8% | 22 |
| registration_date | 72.7% | 22 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 88.3% | 15.7% |
| handwritten:True | 84.1% | 12.5% |
| profile:clean | 97.0% | 9.7% |
| profile:old | 89.2% | 17.5% |
| profile:photo | 64.6% | 26.5% |
| profile:scan | 90.0% | 13.7% |
| template:form_bilingual | 88.7% | 12.7% |
| template:khatauni_table | 82.0% | 19.6% |
| template:ror_english | 97.3% | 9.7% |
