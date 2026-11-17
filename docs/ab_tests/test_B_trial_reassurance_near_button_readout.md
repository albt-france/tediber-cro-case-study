# Test B read-out - '100-night trial' reassurance next to the add-to-cart button
*SIMULATED store. Ran 2026-04-06 to 2026-05-03; 66,972 control and 62,215 variant visitors.*

**1. Allocation check (first).** Variant share 48.16% (chi-square 175.2, p = 5.5e-40) -> **SAMPLE RATIO MISMATCH: the test is not read.**

**2. Results.**

The variant was served by a redirect to a copy of the page. Some visitors never reached it (slow redirect, bots filtered differently, back button), so the two groups are no longer comparable: any difference could come from who was lost, not from the change. The numbers below are shown only to explain why they must not be used: conversion +3.1% (p = 0.43).

**Decision: invalid: fix and relaunch.** Rebuild the variant client-side, run a 48 h allocation check, relaunch for the full planned duration.

**3. Learning.** Check allocation on day 1 and every day; a redirect is a red flag in the QA checklist.

*Read with `src/stats_tests.py` (z test on proportions, bootstrap of revenue per visitor, chi-square SRM). Returns observed up to 30 Nov 2026.*
