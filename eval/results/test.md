# Evaluation — `test` split (40 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 14.2% / 10.9% |
| Field accuracy (all fields) | 88.1% |
| Field accuracy (required fields) | 87.5% |
| Review rate | 67.5% |
| Straight-through accuracy (auto-accepted docs fully correct) | 84.6% |
| Fields flagged for a human (all extracted fields) | 15.3% |
| Precision of fields *not* flagged | 96.4% |
| Auto-accept threshold (calibrated on dev) | 0.9 |
| OCR time per document (CPU) | 30.62 s |
| Owner list exactly right (all documents) | 85.0% |
| Every co-owner found (multi-owner documents) | 6 of 9 |
| Parcel rows recovered (recall / precision) | 62.9% / 65.0% |
| Rows recovered in multi-row tables | 19 of 32 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 90.0% | 40 |
| father_name | 83.3% | 36 |
| khata_number | 87.5% | 40 |
| khasra_number | 77.5% | 40 |
| survey_number | 80.8% | 26 |
| plot_area | 77.5% | 40 |
| land_classification | 95.0% | 40 |
| village | 90.0% | 40 |
| tehsil | 95.0% | 40 |
| district | 95.0% | 40 |
| state | 95.0% | 40 |
| mutation_number | 88.6% | 35 |
| mutation_date | 85.7% | 35 |
| registration_number | 91.3% | 23 |
| registration_date | 87.0% | 23 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 90.6% | 13.5% |
| handwritten:True | 77.4% | 16.8% |
| profile:clean | 98.2% | 10.0% |
| profile:old | 95.3% | 9.4% |
| profile:photo | 56.5% | 30.2% |
| profile:scan | 89.5% | 13.1% |
| template:form_bilingual | 82.6% | 16.4% |
| template:khatauni_table | 84.5% | 14.8% |
| template:ror_english | 96.2% | 11.3% |
