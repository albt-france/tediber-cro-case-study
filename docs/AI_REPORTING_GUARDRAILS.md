# AI in reporting - guardrails

Goal: save time on the weekly note without losing control of its accuracy.

## How the weekly draft is produced
1. `src/weekly_summary.py` builds a **fact sheet** for the week from the tables (KPIs, changes, incidents, mix monitor,
   reconciliation). Only aggregates: no visitor or customer data ever leaves the data layer.
2. A **draft** of 5 to 8 sentences is written:
   - by default with a **sentence template** (deterministic, no key, the version published here);
   - optionally by an LLM (`src/llm_client.py`, only if `.env` sets `LLM_PROVIDER` and `LLM_API_KEY`), told to use the
     fact-sheet numbers only, with their unit, basis and period.
3. **Every number is checked** by `src/check_numbers.py`: metric, segment, unit (% vs pp vs EUR), period (this week /
   week on week / last year / expected), basis (per session / per user, gross / net) and sign. One wrong number rejects
   the draft; a rejected LLM draft falls back to the template.
4. The analyst **reads, edits and signs** the note before it is shared.

## What the checker catches (tested in `tests/test_check_numbers.py`)
- percentage points written as percent, and the reverse;
- wrong reference period (a year-on-year change presented as week on week; an expected value presented as observed);
- conversion per session presented as per user;
- gross revenue presented as net of returns;
- wrong direction (up vs down), and numbers that do not exist in the data.

## What is never delegated
- **Interpretation**: whether a move is a problem, a mix effect, a promotion or a data bug.
- **Decisions**: ship / iterate / drop a test, roll back a release, open an incident.
- **Anything sent outside the team**, and any statement about the company's results.

## How the rest of the study is checked
Every query result is re-computed a second way (SQL vs Python, Excel formulas recalculated by LibreOffice and compared
with Python, statistics vs textbook values in `tests/`), and every public figure is read at its source and dated
(`data/SOURCES.md`).
