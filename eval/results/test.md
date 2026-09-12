# Evaluation — `test` split (40 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 14.3% / 11.1% |
| Field accuracy (all fields) | 86.8% |
| Field accuracy (required fields) | 86.4% |
| Review rate | 70.0% |
| Straight-through accuracy (auto-accepted docs fully correct) | 91.7% |
| Fields flagged for a human (all extracted fields) | 15.7% |
| Precision of fields *not* flagged | 96.4% |
| Auto-accept threshold (calibrated on dev) | 0.88 |
| OCR time per document (CPU) | 31.16 s |
| Owner list exactly right (all documents) | 85.0% |
| Every co-owner found (multi-owner documents) | 6 of 9 |
| Parcel rows recovered (recall / precision) | 58.1% / 60.0% |
| Rows recovered in multi-row tables | 16 of 32 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 90.0% | 40 |
| father_name | 83.3% | 36 |
| khata_number | 82.5% | 40 |
| khasra_number | 75.0% | 40 |
| survey_number | 73.1% | 26 |
| plot_area | 77.5% | 40 |
| land_classification | 95.0% | 40 |
| village | 90.0% | 40 |
| tehsil | 95.0% | 40 |
| district | 95.0% | 40 |
| state | 95.0% | 40 |
| mutation_number | 85.7% | 35 |
| mutation_date | 80.0% | 35 |
| registration_number | 95.7% | 23 |
| registration_date | 87.0% | 23 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 90.2% | 13.5% |
| handwritten:True | 72.8% | 17.2% |
| profile:clean | 97.2% | 10.1% |
| profile:old | 94.4% | 9.4% |
| profile:photo | 55.4% | 30.3% |
| profile:scan | 87.5% | 13.3% |
| template:form_bilingual | 79.7% | 16.6% |
| template:khatauni_table | 84.5% | 14.9% |
| template:ror_english | 95.1% | 11.3% |
