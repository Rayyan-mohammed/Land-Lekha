# Does the confidence number mean anything?

"Why should we trust the confidence?" is the fair question to ask a system that decides which
fields a person has to check. This is the answer, measured on the 516 fields extracted from
the 40 held-out test documents, using the same definition of a correct field as `test.md`.

Reproduce: `python eval/reliability.py --split test`

## Reliability

Fields grouped by the confidence they were given, against how often they were actually right.

| confidence | fields | mean confidence | actually right | gap |
| --- | --- | --- | --- | --- |
| 0.1 – 0.2 | 5 | 0.162 | 0.000 | −0.162 |
| 0.3 – 0.4 | 1 | 0.302 | 1.000 | +0.698 |
| 0.4 – 0.5 | 4 | 0.431 | 0.250 | −0.181 |
| 0.5 – 0.6 | 2 | 0.562 | 0.000 | −0.562 |
| 0.6 – 0.7 | 4 | 0.676 | 0.500 | −0.176 |
| 0.7 – 0.8 | 15 | 0.761 | 0.800 | +0.039 |
| 0.8 – 0.9 | 43 | 0.866 | 0.744 | **−0.122** |
| 0.9 – 1.0 | **442** | 0.958 | 0.964 | **+0.006** |

**Expected calibration error: 0.0245.**

The bin that matters holds 442 of the 516 fields: there the model says 0.958 and is right
0.964 of the time, a gap of six thousandths. The 0.8–0.9 bin is genuinely overconfident by
12 points and is the one real weakness here. The bins below 0.7 hold between one and five
fields each - too few to read anything into, and reported only so nobody thinks they were
hidden.

## Risk against coverage

If only fields at or above a threshold are accepted without a person: how much is accepted,
and how much of what is accepted is wrong.

| threshold | coverage | accepted | wrong | risk |
| --- | --- | --- | --- | --- |
| 0.50 | 98.1% | 506 | 34 | 6.72% |
| 0.70 | 96.9% | 500 | 30 | 6.00% |
| 0.80 | 94.0% | 485 | 27 | 5.57% |
| 0.85 | 91.7% | 473 | 24 | 5.07% |
| **0.90** | **85.7%** | 442 | 16 | **3.62%** |
| 0.95 | 59.7% | 308 | 5 | 1.62% |

This is the curve behind the operating point. Moving from 0.90 to 0.95 halves the risk but
hands a third of the fields back to a person; moving from 0.90 down to 0.80 buys 8 points of
coverage and costs 2 points of risk. The shipped threshold sits at 0.90.

## Honest scope

Synthetic held-out documents, and the calibration was fitted on a separate dev split, not on
these. It has not been measured on real paper, and the number will move when it is.
