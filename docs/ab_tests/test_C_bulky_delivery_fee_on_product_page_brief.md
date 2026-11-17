# Test C brief - Delivery fee shown on bulky-item product pages
*SIMULATED store modelled on public information (its numbers are not Tediber's). Template usable as is.*

**Already on Tediber's public pages?** Yes - the public bed-base page shows the delivery options and the room-delivery fee (17 Nov 2026). The simulated store starts without it.

| Field | Content |
|---|---|
| Problem | In the simulated store, delivery of bed bases, beds and sofas to the room is paid and the fee becomes visible only at the delivery step. Abandonment at that step is twice as high as for other categories. |
| Hypothesis | **Because we saw** shipping-step abandonment of about 40% for bulky items vs about 20% for the other categories, **we believe** showing the delivery fee and options on the product page, before the cart **will cause** fewer bulky-item shoppers to abandon at the delivery step, **measured by** the conversion rate. |
| Variants | Control: current page. Variant: 'Livraison dans la pièce de votre choix : XX EUR, sous 8 à 10 jours' block under the price, with a link to the delivery page. |
| Population / split | visitors who view a bed base, bed or sofa product page; 50/50, by visitor |
| Primary KPI | conversion rate per visitor (bulky-item product-page visitors) |
| Guardrails | add-to-cart rate (expected to fall a little: informed visitors), net revenue per visitor, average order value |
| Baseline / MDE | 1.6% / 16% relative (alpha 5%, power 80%, two-sided) |
| Sample size | 40,672 visitors per variant (81,344 in total) |
| Duration | 49 days at ~1,800 eligible visitors/day (whole weeks) - fixed in advance, no early stop |
| Planned dates | 2026-06-22 to 2026-08-09 |
| Decision rule | SRM -> invalid; primary up (p < 0.05) and no guardrail breached -> ship; primary up but a guardrail breached -> iterate; otherwise drop |
| Risks | Fee shown must match the checkout exactly (QA on 3 postcodes); add-to-cart may fall (not a failure). |

## Pre-launch QA checklist
- [ ] Hypothesis, primary KPI, guardrails, sample size and duration written **before** launch (this brief)
- [ ] Variant renders on iOS Safari, Android Chrome, desktop Chrome/Safari/Edge; no layout shift (CLS) added
- [ ] Variant is served client-side, **no redirect** (redirects lose visitors and create a sample ratio mismatch)
- [ ] Assignment is by visitor and sticky across sessions; returning visitors keep their variant
- [ ] Test-tool events reach analytics (exposure event + variant id); purchases de-duplicated on transaction id
- [ ] A/A or 24 h smoke check: allocation 50/50 (SRM chi-square p > 0.001), no error spike, page speed unchanged
- [ ] No other test on the same pages and audience; no promotion starting during the test window
- [ ] Owner, launch date, end date and decision meeting in the test log
