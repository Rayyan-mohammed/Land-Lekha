# Evaluation — `test` split (40 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 16.7% / 11.3% |
| Field accuracy (all fields) | 82.7% |
| Field accuracy (required fields) | 82.9% |
| Review rate | 85.0% |
| Straight-through accuracy (auto-accepted docs fully correct) | 100.0% |
| Fields flagged for a human (all extracted fields) | 17.7% |
| Precision of fields *not* flagged | 96.4% |
| Auto-accept threshold (calibrated on dev) | 0.88 |
| OCR time per document (CPU) | 33.53 s |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 80.0% | 40 |
| father_name | 67.6% | 37 |
| khata_number | 82.5% | 40 |
| khasra_number | 70.0% | 40 |
| survey_number | 80.8% | 26 |
| plot_area | 72.5% | 40 |
| land_classification | 87.5% | 40 |
| village | 90.0% | 40 |
| tehsil | 90.0% | 40 |
| district | 95.0% | 40 |
| state | 95.0% | 40 |
| mutation_number | 82.1% | 28 |
| mutation_date | 78.6% | 28 |
| registration_number | 84.6% | 26 |
| registration_date | 80.8% | 26 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 85.0% | 16.7% |
| handwritten:True | 75.4% | 16.5% |
| profile:clean | 88.0% | 10.2% |
| profile:old | 83.7% | 17.6% |
| profile:photo | 58.6% | 30.6% |
| profile:scan | 92.3% | 11.7% |
| template:form_bilingual | 81.5% | 16.2% |
| template:khatauni_table | 70.5% | 22.0% |
| template:ror_english | 97.3% | 11.4% |
