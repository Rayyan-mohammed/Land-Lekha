# Demo documents — expected values

Ground truth for each demo file (generated with seed 26018).

## 01-ror-english-clean.jpg
ror_english · clean · handwritten=False

| Field | Expected |
| --- | --- |
| owner_name | Gopal Lal Tiwari |
| khata_number | 00256 |
| khasra_number | 1521/9 |
| survey_number | 26/2 |
| plot_area | 0.77 hectare (0.77 ha) |
| land_classification | barren |
| village | Ratibad |
| tehsil | Huzur |
| district | Bhopal |
| state | Madhya Pradesh |
| registration_number | 1998/51514 |
| registration_date | 19/06/2015 |

## 02-khatauni-table-scan.jpg
khatauni_table · scan · handwritten=False

| Field | Expected |
| --- | --- |
| owner_name | राम वर्मा |
| father_name | सलीम चंद्र वर्मा |
| khata_number | 00879 |
| khasra_number | 1715/6क |
| survey_number | 173/3 |
| plot_area | 0.174 hectare (0.174 ha) |
| land_classification | orchard |
| village | Brijesh Nagar |
| tehsil | Ichhawar |
| district | Sehore |
| state | Madhya Pradesh |
| mutation_number | 9901 |
| mutation_date | 18/07/2002 |

## 03-form-handwritten.jpg
form_bilingual · clean · handwritten=True

| Field | Expected |
| --- | --- |
| owner_name | संजय जाट |
| father_name | अनिल प्रसाद जाट |
| khata_number | 00045 |
| khasra_number | 271 |
| survey_number | 224/5 |
| plot_area | 9.29 bigha (1.5041 ha) |
| land_classification | barren |
| village | Kaladera |
| tehsil | Chomu |
| district | Jaipur |
| state | Rajasthan |
| mutation_number | 8470 |
| mutation_date | 10/05/2022 |
| registration_number | 2011/99488 |
| registration_date | 02/01/2017 |

## 04-old-faded-record.jpg
khatauni_table · old · handwritten=False

| Field | Expected |
| --- | --- |
| owner_name | सरोज वर्मा |
| father_name | हरि प्रसाद वर्मा |
| khata_number | 01001 |
| khasra_number | 205/9 |
| plot_area | 2.704 hectare (2.704 ha) |
| land_classification | pasture |
| village | Nigoha |
| tehsil | Mohanlalganj |
| district | Lucknow |
| state | Uttar Pradesh |
| mutation_number | 9484 |
| mutation_date | 24/08/1996 |

## 05-phone-photo.jpg
khatauni_table · photo · handwritten=False

| Field | Expected |
| --- | --- |
| owner_name | भरत कुमार त्रिपाठी |
| father_name | कृष्ण चंद्र त्रिपाठी |
| khata_number | 1084 |
| khasra_number | 1108/1ख |
| survey_number | 200/6 |
| plot_area | 4.38 bigha (1.1077 ha) |
| land_classification | residential_abadi |
| village | Sujata |
| tehsil | Bodh Gaya |
| district | Gaya |
| state | Bihar |
| mutation_number | 2878 |
| mutation_date | 17/08/1999 |

## 06-scanned-pdf.pdf
form_bilingual · scan · handwritten=True

| Field | Expected |
| --- | --- |
| owner_name | कमला पटेल |
| father_name | हरि पटेल |
| khata_number | 1339 |
| khasra_number | 757/5 |
| survey_number | 285/5 |
| plot_area | 4.228 hectare (4.228 ha) |
| land_classification | agricultural_irrigated |
| village | Brijesh Nagar |
| tehsil | Ichhawar |
| district | Sehore |
| state | Madhya Pradesh |
| mutation_number | 5646 |
| mutation_date | 11/05/2006 |
| registration_number | 2022/47284 |
| registration_date | 04/02/2004 |

## 07-sideways-photo.jpg
Same record as 01, photographed sideways: the pipeline turns it upright (`rotate90`).

| Field | Expected |
| --- | --- |
| owner_name | Gopal Lal Tiwari |
| khata_number | 00256 |
| khasra_number | 1521/9 |
| survey_number | 26/2 |
| plot_area | 0.77 hectare (0.77 ha) |
| land_classification | barren |
| village | Ratibad |
| tehsil | Huzur |
| district | Bhopal |
| state | Madhya Pradesh |
| registration_number | 1998/51514 |
| registration_date | 19/06/2015 |

## 08-born-digital.pdf
Exported by a portal (real text inside): read from the text layer in about a second, no OCR.

| Field | Expected |
| --- | --- |
| owner_name | भरत कुमार मौर्य |
| father_name | कृष्ण चंद्र मौर्य |
| khata_number | 1333 |
| khasra_number | 637 |
| plot_area | 3.787 hectare (3.787 ha) |
| land_classification | orchard |
| village | Achhnera |
| tehsil | Kiraoli |
| district | Agra |
| state | Uttar Pradesh |
| registration_number | 1999/84495 |
| registration_date | 13/06/2012 |
| owners | भरत कुमार मौर्य (s/o कृष्ण चंद्र मौर्य) |
| parcels | 637 = 3.787 hectare, orchard |

## 09-multi-owner-khatauni.jpg
One khata, 3 co-owners and 3 khasra rows.

| Field | Expected |
| --- | --- |
| owner_name | मीना मीणा |
| father_name | प्रकाश चंद्र मीणा |
| khata_number | 3 |
| khasra_number | 445/9 |
| plot_area | 2.453 hectare (2.453 ha) |
| land_classification | orchard |
| village | Karanpur |
| tehsil | Mohanlalganj |
| district | Lucknow |
| state | Uttar Pradesh |
| registration_number | 2014/40702 |
| registration_date | 28/04/1995 |
| owners | मीना मीणा (s/o प्रकाश चंद्र मीणा); कृष्ण प्रसाद मीणा (s/o सुनील प्रसाद मीणा); रेखा मीणा (s/o भरत मीणा) |
| parcels | 445/9 = 2.453 hectare, orchard; 1684/9 = 3.99 hectare, barren; 1377 = 2.548 hectare, barren |
