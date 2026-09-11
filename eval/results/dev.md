# Evaluation — `dev` split (40 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 16.3% / 12.1% |
| Field accuracy (all fields) | 84.6% |
| Field accuracy (required fields) | 83.2% |
| Review rate | 87.5% |
| Straight-through accuracy (auto-accepted docs fully correct) | 100.0% |
| Fields flagged for a human (all extracted fields) | 30.2% |
| Precision of fields *not* flagged | 97.0% |
| Auto-accept threshold (calibrated on dev) | 0.89 |
| OCR time per document (CPU) | 15.7 s |
| Owner list exactly right (all documents) | 80.0% |
| Every co-owner found (multi-owner documents) | 8 of 13 |
| Parcel rows recovered (recall / precision) | 59.5% / 60.3% |
| Rows recovered in multi-row tables | 29 of 51 |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 90.0% | 40 |
| father_name | 81.1% | 37 |
| khata_number | 95.0% | 40 |
| khasra_number | 70.0% | 40 |
| survey_number | 86.2% | 29 |
| plot_area | 77.5% | 40 |
| land_classification | 90.0% | 40 |
| village | 80.0% | 40 |
| tehsil | 80.0% | 40 |
| district | 90.0% | 40 |
| state | 92.5% | 40 |
| mutation_number | 82.9% | 35 |
| mutation_date | 91.4% | 35 |
| registration_number | 77.3% | 22 |
| registration_date | 81.8% | 22 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 85.3% | 16.9% |
| handwritten:True | 82.8% | 12.6% |
| profile:clean | 95.6% | 9.9% |
| profile:old | 81.5% | 21.2% |
| profile:photo | 59.6% | 27.8% |
| profile:scan | 88.5% | 14.4% |
| template:form_bilingual | 88.0% | 12.8% |
| template:khatauni_table | 76.6% | 21.7% |
| template:ror_english | 97.3% | 9.7% |
