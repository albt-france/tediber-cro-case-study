# Test B brief - '100-night trial' reassurance next to the add-to-cart button
*SIMULATED store modelled on public information (its numbers are not Tediber's). Template usable as is.*

**Already on Tediber's public pages?** Yes - trial and free returns are listed right under the button on the public mattress page (17 Nov 2026).

| Field | Content |
|---|---|
| Problem | In the simulated store, the 100-night trial and free return appear far from the add-to-cart button on product pages. |
| Hypothesis | **Because we saw** the trial promise is shown in the header banner and lower on the page, not next to the button, **we believe** a short '100 nuits d'essai, retour gratuit' line right under the button **will cause** more product-page visitors to order, **measured by** the conversion rate. |
| Variants | Control: current page. Variant: one line with icon under the button, linking to the trial page. |
| Population / split | visitors who view a product page; 50/50, by visitor |
| Primary KPI | conversion rate per visitor (product-page visitors) |
| Guardrails | 100-night return rate, net revenue per visitor, add-to-cart rate |
| Baseline / MDE | 2.0% / 12% relative (alpha 5%, power 80%, two-sided) |
| Sample size | 56,548 visitors per variant (113,096 in total) |
| Duration | 28 days at ~4,600 eligible visitors/day (whole weeks) - fixed in advance, no early stop |
| Planned dates | 2026-04-06 to 2026-05-03 |
| Decision rule | SRM -> invalid; primary up (p < 0.05) and no guardrail breached -> ship; primary up but a guardrail breached -> iterate; otherwise drop |
| Risks | Variant built as a redirect to a copy of the page (first run): any redirect must be avoided or checked for SRM daily. |

## Pre-launch QA checklist
- [ ] Hypothesis, primary KPI, guardrails, sample size and duration written **before** launch (this brief)
- [ ] Variant renders on iOS Safari, Android Chrome, desktop Chrome/Safari/Edge; no layout shift (CLS) added
- [ ] Variant is served client-side, **no redirect** (redirects lose visitors and create a sample ratio mismatch)
- [ ] Assignment is by visitor and sticky across sessions; returning visitors keep their variant
- [ ] Test-tool events reach analytics (exposure event + variant id); purchases de-duplicated on transaction id
- [ ] A/A or 24 h smoke check: allocation 50/50 (SRM chi-square p > 0.001), no error spike, page speed unchanged
- [ ] No other test on the same pages and audience; no promotion starting during the test window
- [ ] Owner, launch date, end date and decision meeting in the test log
