# Telugu, end to end

The PS lists multilingual recognition first. Until now the reader was fixed to Hindi and
English, so a page printed in Telugu read as noise and produced **no fields at all**. This is
what it does now, measured on six generated Pahani/Adangal pages with typed ground truth.

| Measure | Result |
| --- | --- |
| Reader chosen correctly (te+en, not the hi+en default) | **6 / 6** |
| Script named correctly from the text | **6 / 6** |
| Typed fields recovered (khata, survey, owner, father, extent) | **19 / 30 = 63.3%** |
| Place names resolved to their LGD English names | **18 / 18 = 100%** |
| Time per page, CPU, including the second read | ~75 s |

Before this change all five columns were zero: the page was unreadable, so nothing followed.

## How the reader is chosen

Text detection is script-agnostic, so the boxes are found once. A sample of twelve of them is
then re-read with each candidate reader and the most confident wins - the same trick the
upside-down check has always used. On the first page of the set:

| Reader | Mean confidence on the same twelve boxes |
| --- | --- |
| **te+en** | **0.658** |
| kn+en | 0.490 |
| bn+en | 0.301 |
| hi+en | 0.230 |

A win must beat the default by 0.05 or the default stands: swapping readers costs seconds and
several hundred megabytes, and noise is not a reason to pay it. A Hindi page therefore pays
one extra sample of twelve boxes and nothing else.

EasyOCR will not put two Indic scripts in one reader, so each travels with English and the
engine keeps one reader per set, built on first use.

## What the 63.3% is made of

Place names are the strong column, because the LGD gazetteer resolves what OCR reads to the
official name: `ఇబ్రహీంపట్నం` became Ibrahimpatnam, `రంగారెడ్డి` became Ranga Reddy,
`తెలంగాణ` became Telangana. Nothing was translated - the page's own text is kept as written
and the gazetteer is consulted separately.

The weak column is names. Telugu conjuncts are where the recogniser loses characters
(`పట్టాదారు` came back as `పట్టడరు` on two pages), and a name that is one character out is
counted wrong here, as it should be. Those fields carry low confidence and go to a verifier,
which is the system behaving correctly rather than a hidden failure.

## Honest scope

These six pages are **generated**, printed in Nirmala UI on clean white, and they are not a
substitute for real Telangana Pahani paper. They prove the routing, the labels and the units
work end to end; they do not tell you how the recogniser handles a real scanned register.
Real documents are the next step and the numbers will be reported separately when they exist.

Reproduce: `eval/telugu_eval.py` (set builder and scorer), ground truth beside each page.
