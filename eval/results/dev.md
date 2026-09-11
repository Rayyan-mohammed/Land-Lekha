# Evaluation — `dev` split (40 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 16.5% / 11.8% |
| Field accuracy (all fields) | 89.0% |
| Field accuracy (required fields) | 86.1% |
| Review rate | 75.0% |
| Straight-through accuracy (auto-accepted docs fully correct) | 100.0% |
| Fields flagged for a human (all extracted fields) | 16.2% |
| Precision of fields *not* flagged | 98.6% |
| Auto-accept threshold (calibrated on dev) | 0.88 |
| OCR time per document (CPU) | 29.18 s |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 87.5% | 40 |
| father_name | 83.8% | 37 |
| khata_number | 87.5% | 40 |
| khasra_number | 80.0% | 40 |
| survey_number | 85.7% | 28 |
| plot_area | 75.0% | 40 |
| land_classification | 92.5% | 40 |
| village | 95.0% | 40 |
| tehsil | 85.0% | 40 |
| district | 92.5% | 40 |
| state | 95.0% | 40 |
| mutation_number | 96.7% | 30 |
| mutation_date | 96.7% | 30 |
| registration_number | 95.2% | 21 |
| registration_date | 95.2% | 21 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 88.2% | 17.2% |
| handwritten:True | 90.5% | 12.8% |
| profile:clean | 100.0% | 8.2% |
| profile:old | 100.0% | 18.2% |
| profile:photo | 70.6% | 24.5% |
| profile:scan | 92.2% | 15.3% |
| template:form_bilingual | 86.7% | 15.3% |
| template:khatauni_table | 81.5% | 23.6% |
| template:ror_english | 95.4% | 12.4% |
