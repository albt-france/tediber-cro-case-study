# KPI dictionary

One definition per KPI, the formula used in `sql/` and in the Excel workbook, the source, and the traps.
"Source of truth" = the shop back office for orders, revenue and returns; analytics (GA4) for sessions and steps.

| KPI | Definition | Formula | Source | Traps |
|---|---|---|---|---|
| Sessions | Visits to the site | count of sessions | Analytics | Bots and consent refusals change the count; compare like with like (same consent rules). |
| Conversion rate per session | Share of sessions with an order | orders / sessions | Shop orders / analytics sessions | A mattress is bought after several visits: per session it looks low and falls when people browse more. Always say "per session". |
| Conversion rate per user | Share of visitors who order within the period | orders / distinct users | Analytics users | Depends on cookie lifetime and devices (one person = several users). Better for long purchase cycles; say "per user". |
| Average order value (AOV) | Average basket | revenue / orders | Shop | Falls during promotions while revenue rises; a few sofa orders move it a lot (use the median too). |
| Revenue per visit (RPV) | Revenue earned per session | revenue / sessions = conversion x AOV | Shop + analytics | Combines conversion and basket: the primary money metric of a test. Heavy-tailed: use the bootstrap for intervals. |
| Net revenue per visit | Revenue per session after 100-night returns | (revenue - returned revenue) / sessions | Shop (returns) | Returns arrive up to ~100 days later: recent weeks look better than they will be. Report "returns observed so far" and re-read later. |
| Add-to-cart rate | Share of sessions (or product views, or visitors) with an add to cart | add-to-cart sessions / sessions | Analytics | Three denominators exist: say which. A higher add-to-cart rate is not a win if checkout falls. |
| Checkout abandonment | Share of checkouts that do not end in an order | 1 - orders / checkout starts | Analytics + shop | Includes payment failures and bulky-delivery fees; split by step (shipping, payment) to find the leak. |
| Step pass rate | Share of sessions reaching step n+1 among those reaching step n | step n+1 / step n | Analytics | Open funnel (any order) vs closed funnel (strict order) give different numbers. This study uses open funnels. |
| Return rate | Share of orders returned within the trial | returned orders / orders | Shop | Cohort by order date, not by return date. Mattresses (100 nights) vs linen (30 nights). |
| Revenue ratio analytics / shop | Analytics revenue as a share of shop revenue | analytics revenue / shop revenue | Both | Normally slightly below 100 % (consent, ad-blockers). **Above 100 % = purchases counted twice**: de-duplicate on transaction id. |
| Sample ratio (SRM) | Share of visitors in each variant vs plan | chi-square goodness of fit | Testing tool | p < 0.001 means the allocation is broken: do not read the test. |
| Minimum detectable effect (MDE) | Smallest relative lift the test can detect with 80 % power | see `stats_tests.sample_size_per_arm` | - | Choose it before launch from the traffic you have, not after seeing the result. |

## Percent vs percentage points
Conversion going from 1.20 % to 1.08 % is **-0.12 pp** (points) or **-10 %** (relative). Writing "-0.12 %" is wrong
and is one of the errors the number checker (`src/check_numbers.py`) rejects.

## Mix vs rate
A topline rate can move only because the traffic mix moved (e.g. more cold paid-social visits) while every
segment converts as before (Simpson's paradox). Before opening an incident, compare the rate inside segments
(`sql/03_anomalies.sql`, rate / mix decomposition).
