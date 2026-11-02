# BrandLens evaluation report

Mode: **rule engine only**. Set: holdout. Posts: 15. Labelled issues: 16. Run on 31 Oct 2026.

| Category | Correct flags | False alarms | Missed | Precision | Recall |
|---|---|---|---|---|---|
| Claim | 2 | 1 | 4 | 67% | 33% |
| Terminology | 2 | 0 | 0 | 100% | 100% |
| Tone | 3 | 1 | 1 | 75% | 75% |
| Accessibility | 1 | 0 | 0 | 100% | 100% |
| Disclosure | 2 | 1 | 1 | 67% | 67% |
| **All** | 10 | 3 | 6 | **77%** | **62%** |

## Missed issues (not flagged)

- H03 [Claim] Dermatologists across the country swear by our night serum
- H04 [Claim] Say goodbye to eczema flare-ups for good
- H05 [Claim] works on absolutely everyone
- H06 [Claim] 500 volunteers
- H14 [Tone] you are doing skincare wrong
- H10 [Disclosure] (no single span)

## False alarms (flagged but not in the labels)

- H12 [Claim] 'best' (rule)
- H10 [Tone] 'GLOW' (rule)
- H13 [Disclosure] '' (rule)
