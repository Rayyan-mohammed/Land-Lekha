# Handwriting: what has actually been measured

The problem statement names handwritten records twice, so this number deserves to be stated
precisely rather than rounded into a headline.

## Scope — read this first

Every figure below is on **handwriting-font pages**: the generator renders the entries in
Kalam, a Devanagari handwriting typeface, in a browser, then degrades the page (scan noise,
fading, skew, phone-photo perspective). That is handwriting-*shaped* text with even stroke
weight and perfect letterforms.

**Real ink has not been measured.** No pen-written land record has been through this system.
Real handwriting varies in slant, pressure, spacing and baseline in ways a font does not, and
joins characters in ways a font does not. The honest expectation is that these numbers are an
upper bound, and the gap to real paper is unknown until someone supplies a register page.

## The numbers

| Split | Handwriting-font pages | Field accuracy | Median CER | Printed pages | Field accuracy | Median CER |
| --- | --- | --- | --- | --- | --- | --- |
| dev | 6 | 85.0% | 13.2% | 34 | 88.3% | 11.4% |
| test | 9 | **77.4%** | 12.8% | 31 | 90.6% | 10.5% |
| multi | 12 | 74.5% | 14.7% | 18 | 92.5% | 13.2% |
| **all three** | **27** | **77.8%** | **13.2%** | **83** | **90.1%** | **11.4%** |

So handwriting-font pages cost about **12 points of field accuracy** against printed ones,
while character error rate barely moves (13.2% against 11.4%).

## Where handwriting actually hurts

That combination - much worse fields, barely worse characters - says the damage is
concentrated. Counting how often each field is wrong on handwriting pages against printed
ones, across all 110 documents:

| Field | Wrong on handwriting | Wrong on printed |
| --- | --- | --- |
| mutation_number | 10 | 5 |
| khata_number | 6 | 2 |
| survey_number | 6 | 3 |
| mutation_date | 8 | 6 |
| khasra_number | 10 | 14 |
| father_name | 5 | 10 |
| village | 5 | 9 |

The identifiers suffer and the names do not. Names and places have help that numbers do not:
a name lexicon, and the LGD gazetteer that can resolve a misread village to a real one. A
khata number has no such backstop - every digit has to be right, and a handwritten digit is
where the recogniser is least sure. This is the same weakness the English-only number re-read
was built for, and it is worth more on handwriting than anywhere else.

## Worst pages

`multi-014` (handwriting on a phone photo) scored 0% and was correctly rejected by the quality
check. `multi-004`, `test-018` and `test-039` sit between 57% and 67%. The pattern is
handwriting plus a second difficulty - a photograph, or old faded paper - rather than
handwriting alone.

Reproduce from the per-document tables in `dev.json`, `test.json` and `multi.json`
(`handwritten: true`).
