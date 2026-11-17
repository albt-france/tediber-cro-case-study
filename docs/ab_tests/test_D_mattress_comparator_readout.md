# Test D read-out - Mattress comparator
*SIMULATED store. Ran 2026-08-31 to 2026-10-25; 168,253 control and 167,854 variant visitors.*

**1. Allocation check (first).** Variant share 49.94% (chi-square 0.5, p = 4.9e-01) -> allocation OK.

**2. Results.**

| Metric | Control | Variant | Lift [95% CI] | p-value |
|---|---|---|---|---|
| conversion rate (primary) | 1.56% | 1.69% | +8.1% [+2.6%; +13.6%] | 0.0038 |
| Revenue per visitor (gross) | EUR 10.01 | EUR 10.60 | +6.0% [-0.1%; +12.4%] | bootstrap |
| Revenue per visitor (net of returns) | EUR 9.22 | EUR 9.49 | +2.9% [-3.4%; +9.6%] | 0.36 |
| 100-night return rate (guardrail) | 7.6% | 10.9% | | < 0.0001 |

**Decision: ITERATE.** 

**3. Learning.** A higher conversion is not a win if returns rise: the comparator helps people decide but not always choose the right firmness. Next: add a firmness guide / sleep-position question, re-test with net revenue per visitor as the primary metric, after returns have matured.

*Read with `src/stats_tests.py` (z test on proportions, bootstrap of revenue per visitor, chi-square SRM). Returns observed up to 30 Nov 2026.*
