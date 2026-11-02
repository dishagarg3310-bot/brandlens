# BrandLens evaluation report

Mode: **rules + AI layer (gemini)**. Set: holdout. Posts: 15. Labelled issues: 16. Run on 02 Nov 2026.

| Category | Correct flags | False alarms | Missed | Precision | Recall |
|---|---|---|---|---|---|
| Claim | 4 | 1 | 2 | 80% | 67% |
| Terminology | 2 | 0 | 0 | 100% | 100% |
| Tone | 4 | 5 | 0 | 44% | 100% |
| Accessibility | 1 | 0 | 0 | 100% | 100% |
| Disclosure | 2 | 1 | 1 | 67% | 67% |
| Messaging | 0 | 2 | 0 | 0% | 0% |
| **All** | 13 | 9 | 3 | **59%** | **81%** |

## Missed issues (not flagged)

- H04 [Claim] Say goodbye to eczema flare-ups for good
- H05 [Claim] works on absolutely everyone
- H10 [Disclosure] (no single span)

## False alarms (flagged but not in the labels)

- H12 [Claim] 'best' (rule)
- H08 [Tone] 'cheerful' (ai)
- H09 [Tone] 'The glow-up' (ai)
- H10 [Tone] 'GLOW' (rule)
- H10 [Messaging] 'Partnering with GreenLeaf this month' (ai)
- H15 [Messaging] '#sponsored' (ai)
- H11 [Tone] 'The aforementioned dermatological formulation necessitates application subsequent to cleansing, whereupon epidermal permeability is demonstrably augmented, facilitating enhanced absorption of subsequent compounds.' (ai)
- H13 [Disclosure] '' (rule)
- H13 [Tone] 'Diwali glow ke liye hamara naya ubtan face pack!' (ai)
