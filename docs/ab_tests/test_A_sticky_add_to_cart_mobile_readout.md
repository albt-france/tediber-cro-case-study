# Test A read-out - Sticky add-to-cart button on mobile product pages
*SIMULATED store. Ran 2026-02-09 to 2026-03-08; 43,275 control and 43,305 variant visitors.*

**1. Allocation check (first).** Variant share 50.02% (chi-square 0.0, p = 9.2e-01) -> allocation OK.

**2. Results.**

| Metric | Control | Variant | Lift [95% CI] | p-value |
|---|---|---|---|---|
| add-to-cart rate (primary) | 9.02% | 9.77% | +8.3% [+4.0%; +12.6%] | 0.0002 |
| Revenue per visitor (gross) | EUR 10.93 | EUR 11.56 | +5.8% [-5.2%; +18.4%] | bootstrap |
| Revenue per visitor (net of returns) | EUR 10.29 | EUR 10.65 | +3.5% [-7.8%; +16.5%] | 0.56 |
| 100-night return rate (guardrail) | 6.0% | 7.6% | | 0.2040 |
| Conversion rate (secondary) | | | +2.8% | 0.58 |

**Decision: SHIP.** Annualised effect on net revenue if the lift holds: EUR 0.4 M (95% range EUR -0.9 M to 1.9 M) - SIMULATED store; the range, not the central value, is what we commit to.

**3. Learning.** The primary metric moved clearly; revenue per visitor is too noisy to read at this sample size, so the decision rests on the primary metric plus guardrails not breached. Follow conversion after launch.

*Read with `src/stats_tests.py` (z test on proportions, bootstrap of revenue per visitor, chi-square SRM). Returns observed up to 30 Nov 2026.*
