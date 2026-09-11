# Evaluation — `multi` split (30 documents)

| Metric | Value |
| --- | --- |
| CER (mean / median) | 16.8% / 13.8% |
| Field accuracy (all fields) | 81.4% |
| Field accuracy (required fields) | 80.5% |
| Review rate | 73.3% |
| Straight-through accuracy (auto-accepted docs fully correct) | 100.0% |
| Fields flagged for a human (all extracted fields) | 15.8% |
| Precision of fields *not* flagged | 96.3% |
| Auto-accept threshold (calibrated on dev) | 0.88 |
| OCR time per document (CPU) | 29.57 s |
| All co-owners found (7 multi-owner docs) | 70.0% |
| Parcel rows recovered (recall / precision) | 59.5% / 61.0% |

## Per field

| Field | Accuracy | n |
| --- | --- | --- |
| owner_name | 70.0% | 30 |
| father_name | 71.4% | 28 |
| khata_number | 80.0% | 30 |
| khasra_number | 80.0% | 30 |
| survey_number | 77.8% | 18 |
| plot_area | 63.3% | 30 |
| land_classification | 93.3% | 30 |
| village | 93.3% | 30 |
| tehsil | 83.3% | 30 |
| district | 93.3% | 30 |
| state | 93.3% | 30 |
| mutation_number | 92.3% | 26 |
| mutation_date | 73.1% | 26 |
| registration_number | 77.8% | 18 |
| registration_date | 72.2% | 18 |

## By document group (field accuracy / CER)

| Group | Field acc. | CER |
| --- | --- | --- |
| handwritten:False | 84.9% | 17.3% |
| handwritten:True | 72.5% | 15.6% |
| profile:clean | 92.1% | 9.7% |
| profile:old | 77.5% | 20.3% |
| profile:photo | 50.7% | 30.8% |
| profile:scan | 90.5% | 13.2% |
| template:form_bilingual | 79.1% | 16.4% |
| template:khatauni_table | 67.0% | 20.3% |
| template:ror_english | 94.7% | 14.8% |
