# The first real documents

Until now every number in this repository came from generated pages. These are the first real
land documents measured end to end: three registered deeds on non-judicial stamp paper, from
Andhra Pradesh, West Bengal and Haryana. The documents and their typed ground truth stay off the
public repository (`data/real/` is ignored by git); this page carries counts and field names only.

Reproduce, with the documents in place: `python eval/real_eval.py`

## Result

| | First run | After fixes |
| --- | --- | --- |
| Fields right | 1 / 11 = **9.1%** | 2 / 11 = **18.2%** |
| Document type named correctly | 0 / 3 | 0 / 3 |
| Auto-accepted into the register | 0 / 3 | 0 / 3 |

**The "after fixes" column is not an unseen result.** The one field it gained came from a change
prompted by the same document it was measured on (`Dist.` added as a district label). An honest
unseen number needs documents that were not used to find the fixes.

Nothing reached the register on its own. All three went to a person - which, at 9-18% of fields
right, is the system behaving correctly, not a consolation.

## Why so low: three separate causes

**1. The master data does not cover these states.** The gazetteer holds Uttar Pradesh, Madhya
Pradesh, Rajasthan, Bihar, Andhra Pradesh and Telangana. West Bengal and Haryana are not in it,
and 8 of the 11 ground-truth fields are places in those two states - they can never be validated
against master data, only read verbatim. This is coverage, not reading.

**2. The recogniser garbles printed English on these pages.** On the West Bengal deed the Hindi +
English model turned E into D throughout: "DEED OF GIFT" came back as `DDDD OD GIDT`, "BETWEEN"
as `BBWbDN`, "TEACHERS" as `TBACHDRS`. With the title unrecoverable, the document type cannot be
named - which is why all three are "unknown", even though the type list now knows every one of
these titles.

**3. Page one of a deed is the wrong page.** It carries the stamp, the parties and the value. The
parcel schedule - survey number, extent, boundaries - is on later pages that were not supplied.
The Andhra Pradesh page has exactly one schema field printed on it.

## What measuring found, beyond the score

Getting these three pages through the pipeline turned up four real defects, now fixed:

* **Pages mentioning cents or guntas crashed extraction.** Both units had been added to the
  Telugu vocabulary without a conversion. The West Bengal deed is measured in cents.
* **Kanal was silently read as hectares.** `8 कनाल 16 मरला` became 8 hectares instead of 0.45 -
  twenty times too big, on every Haryana and Punjab record.
* **An upright form was turned sideways.** The Haryana deed's two aligned columns fooled the
  orientation test; it was rotated, read as noise, and routed to the Kannada recogniser. A
  proposed turn is now confirmed by reading the page both ways (`eval/results/orientation.md`).
* **Deed titles in the order offices print them** - "DEED OF GIFT", `पट्टानामा`, `విక్రయ పత్రము` -
  were not recognised; the list only knew "gift deed".

One idea was tested and rejected: reading mostly-English pages with the English-only recogniser.
It read these deeds better, but on 320 fields of synthetic English pages it scored 95.3% against
96.6%, and a change that lowers the benchmark does not go in on two pages
(`eval/results/experiments.md`, section 14).

## What this does and does not show

Three documents, all page one of a registered deed, ground truth typed by one reader. That is far
too little to state an accuracy for real paper, and none of these is a Khatauni - the kind of
record the extractor was built around. What it does show is where the system breaks on real
paper, and that it fails safely: low scores, flagged, nothing invented, nothing auto-accepted.

The next step is not more fixes against these three. It is more documents - Khataunis and
Record-of-Rights extracts from public portals especially - with ground truth typed by two people
independently, and a portion held back that no fix is ever tuned on.
