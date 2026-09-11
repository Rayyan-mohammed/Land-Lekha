# Evaluation — `dev` split (40 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 14.8% / 11.2% |
| Field accuracy (all fields) | 89.2% |
| Field accuracy (required fields) | 87.9% |
| Review rate | 70.0% |
| Straight-through accuracy (auto-accepted docs fully correct) | 91.7% |
| Fields flagged for a human (all extracted fields) | 14.6% |
| Precision of fields *not* flagged | 97.5% |
| Auto-accept threshold (calibrated on dev) | 0.88 |
| OCR time per document (CPU) | 156.93 s |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 87.5% | 40 |
| father_name | 83.8% | 37 |
| khata_number | 87.5% | 40 |
| khasra_number | 87.5% | 40 |
| survey_number | 85.7% | 28 |
| plot_area | 80.0% | 40 |
| land_classification | 90.0% | 40 |
| village | 87.5% | 40 |
| tehsil | 87.5% | 40 |
| district | 97.5% | 40 |
| state | 97.5% | 40 |
| mutation_number | 96.7% | 30 |
| mutation_date | 93.3% | 30 |
| registration_number | 90.5% | 21 |
| registration_date | 85.7% | 21 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 89.5% | 15.3% |
| handwritten:True | 85.6% | 11.6% |
| profile:clean | 100.0% | 8.2% |
| profile:old | 96.2% | 17.2% |
| profile:photo | 71.6% | 20.6% |
| profile:scan | 92.7% | 13.9% |
| template:form_bilingual | 85.8% | 13.7% |
| template:khatauni_table | 82.6% | 20.8% |
| template:ror_english | 96.4% | 11.3% |
