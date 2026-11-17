# Weekly CRO report - template (one page, Monday)

**Week of:** `<Monday date>` · **Compared with:** previous week and same week last year · **Data checked:** analytics vs shop ratio `<x %>` (OK / alert)

## 1. Headline (3 lines max)
What moved, why (or "cause not found yet"), what we do. Numbers with their unit (% vs pp), basis (per session /
per user, gross / net) and period.

## 2. KPIs
| KPI | This week | Week on week | Same week LY | Status |
|---|---|---|---|---|
| Sessions | | | | |
| Conversion per session | | (pp and %) | | |
| Conversion per user | | | | |
| Average order value | | | | |
| Revenue per visit (gross / net of returns) | | | | |
| Add-to-cart rate | | | | |
| Checkout abandonment (shipping / payment steps) | | | | |
Status: RED <= -5 %, AMBER <= -2 % (Excel "Weekly report" tab). Promotion weeks are compared with last year's promotion.

## 3. Alerts and triage
| Alert | Segment | Size (vs expected) | Mix effect? | Release in the 10 days before | Status | Owner |
|---|---|---|---|---|---|---|
Rule: no incident is opened before (1) checking the traffic mix and (2) checking the data (reconciliation).

## 4. Tests running
| Test | Day x / planned | Allocation (SRM) | Guardrails | Note |
|---|---|---|---|---|
No result is read before the planned end date.

## 5. Decisions and next actions (3 max)
| Action | Owner | Due |
|---|---|---|

*Automatic draft: `python src/weekly_summary.py --week <date>`; every number is checked by `src/check_numbers.py`;
the analyst reads, corrects and signs the note before sending.*
