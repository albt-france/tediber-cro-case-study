# Test D brief - Mattress comparator
*SIMULATED store modelled on public information (its numbers are not Tediber's). Template usable as is.*

**Already on Tediber's public pages?** Yes - the public mattress pages show a comparator and a 'Quel matelas choisir ?' quiz (17 Nov 2026). Its effect on returns is not observable from outside.

| Field | Content |
|---|---|
| Problem | In the simulated store, several mattress models with different firmness and prices: visitors open several product pages and come back several times before choosing. |
| Hypothesis | **Because we saw** multi-session journeys and a high share of mattress returns within the 100 nights, **we believe** a side-by-side comparator (firmness, height, materials, price) reachable from every mattress page **will cause** more visitors to choose a mattress and order, **measured by** the conversion rate. |
| Variants | Control: no comparator. Variant: 'Comparer nos matelas' table in the menu and on mattress pages. |
| Population / split | all visitors; 50/50, by visitor |
| Primary KPI | conversion rate per visitor (all visitors) |
| Guardrails | 100-night return rate (mattresses), net revenue per visitor after returns, average order value |
| Baseline / MDE | 1.6% / 8% relative (alpha 5%, power 80%, two-sided) |
| Sample size | 156,774 visitors per variant (313,548 in total) |
| Duration | 56 days at ~6,000 eligible visitors/day (whole weeks) - fixed in advance, no early stop |
| Planned dates | 2026-08-31 to 2026-10-25 |
| Decision rule | SRM -> invalid; primary up (p < 0.05) and no guardrail breached -> ship; primary up but a guardrail breached -> iterate; otherwise drop |
| Risks | Easier choice may also mean a wrong choice (returns): read on net revenue, wait for returns to mature. |

## Pre-launch QA checklist
- [ ] Hypothesis, primary KPI, guardrails, sample size and duration written **before** launch (this brief)
- [ ] Variant renders on iOS Safari, Android Chrome, desktop Chrome/Safari/Edge; no layout shift (CLS) added
- [ ] Variant is served client-side, **no redirect** (redirects lose visitors and create a sample ratio mismatch)
- [ ] Assignment is by visitor and sticky across sessions; returning visitors keep their variant
- [ ] Test-tool events reach analytics (exposure event + variant id); purchases de-duplicated on transaction id
- [ ] A/A or 24 h smoke check: allocation 50/50 (SRM chi-square p > 0.001), no error spike, page speed unchanged
- [ ] No other test on the same pages and audience; no promotion starting during the test window
- [ ] Owner, launch date, end date and decision meeting in the test log
