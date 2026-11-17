# Test C read-out - Delivery fee shown on bulky-item product pages
*SIMULATED store. Ran 2026-06-22 to 2026-08-09; 43,860 control and 43,627 variant visitors.*

**1. Allocation check (first).** Variant share 49.87% (chi-square 0.6, p = 4.3e-01) -> allocation OK.

**2. Results.**

| Metric | Control | Variant | Lift [95% CI] | p-value |
|---|---|---|---|---|
| conversion rate (primary) | 1.56% | 1.87% | +19.8% [+8.8%; +30.8%] | 0.0004 |
| Revenue per visitor (gross) | EUR 10.10 | EUR 12.23 | +21.1% [+7.9%; +36.5%] | bootstrap |
| Revenue per visitor (net of returns) | EUR 9.25 | EUR 11.24 | +21.4% [+7.8%; +37.7%] | 0.00 |
| 100-night return rate (guardrail) | 8.6% | 7.5% | | 0.4174 |

**Decision: SHIP.** Annualised effect on net revenue if the lift holds: EUR 1.3 M (95% range EUR 0.5 M to 2.3 M) - SIMULATED store; the range, not the central value, is what we commit to.

**3. Learning.** Showing a cost early lowers add-to-cart a little but removes the bad surprise at checkout: judge the full funnel, not one step. The test ran while the purchase tag was duplicated in analytics; it was read from the testing tool and the back office, so it is not affected.

*Read with `src/stats_tests.py` (z test on proportions, bootstrap of revenue per visitor, chi-square SRM). Returns observed up to 30 Nov 2026.*
