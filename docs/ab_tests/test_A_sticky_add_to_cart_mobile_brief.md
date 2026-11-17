# Test A brief - Sticky add-to-cart button on mobile product pages
*SIMULATED store modelled on public information (its numbers are not Tediber's). Template usable as is.*

**Already on Tediber's public pages?** Yes - the public mattress page shows a sticky price + add-to-cart bar on mobile (17 Nov 2026). This brief shows how such a feature is measured.

| Field | Content |
|---|---|
| Problem | In the simulated store, on mobile product pages the add-to-cart button leaves the screen as soon as the visitor scrolls through photos, sizes and reviews. Mobile add-to-cart rate is well below desktop in the weekly report. |
| Hypothesis | **Because we saw** mobile visitors scroll long product pages and add to cart less often than desktop visitors, **we believe** keeping the add-to-cart button visible (sticky bar with price and size) **will cause** more mobile visitors to add a mattress or pillow to the cart, **measured by** the add-to-cart rate. |
| Variants | Control: current page. Variant: sticky bottom bar (price + selected size + 'Ajouter au panier') once the main button scrolls out of view. |
| Population / split | mobile visitors who view a product page; 50/50, by visitor (cookie) |
| Primary KPI | add-to-cart rate per visitor (mobile product-page visitors) |
| Guardrails | conversion rate per visitor, net revenue per visitor, 100-night return rate, page speed (LCP) |
| Baseline / MDE | 9.0% / 7% relative (alpha 5%, power 80%, two-sided) |
| Sample size | 33,406 visitors per variant (66,812 in total) |
| Duration | 28 days at ~3,100 eligible visitors/day (whole weeks) - fixed in advance, no early stop |
| Planned dates | 2026-02-09 to 2026-03-08 |
| Decision rule | SRM -> invalid; primary up (p < 0.05) and no guardrail breached -> ship; primary up but a guardrail breached -> iterate; otherwise drop |
| Risks | Bar hiding the chat or cookie banner; double tap on the button; layout shift (CLS). |

## Pre-launch QA checklist
- [ ] Hypothesis, primary KPI, guardrails, sample size and duration written **before** launch (this brief)
- [ ] Variant renders on iOS Safari, Android Chrome, desktop Chrome/Safari/Edge; no layout shift (CLS) added
- [ ] Variant is served client-side, **no redirect** (redirects lose visitors and create a sample ratio mismatch)
- [ ] Assignment is by visitor and sticky across sessions; returning visitors keep their variant
- [ ] Test-tool events reach analytics (exposure event + variant id); purchases de-duplicated on transaction id
- [ ] A/A or 24 h smoke check: allocation 50/50 (SRM chi-square p > 0.001), no error spike, page speed unchanged
- [ ] No other test on the same pages and audience; no promotion starting during the test window
- [ ] Owner, launch date, end date and decision meeting in the test log
