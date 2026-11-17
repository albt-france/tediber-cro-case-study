"""The number checker must pass a correct note and catch every trap (pytest)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import check_numbers as cn  # noqa: E402

SHEET = {"facts": [
    {"metric": "sessions", "segment": "All", "value": 62483, "unit": "count", "period": "current", "basis": None, "label": "sessions"},
    {"metric": "sessions", "segment": "All", "value": -0.32, "unit": "pct", "period": "wow", "basis": None, "label": "sessions wow"},
    {"metric": "sessions", "segment": "All", "value": 8.1, "unit": "pct", "period": "yoy", "basis": None, "label": "sessions yoy"},
    {"metric": "conversion", "segment": "All", "value": 1.0712, "unit": "pct", "period": "current", "basis": "per_session", "label": "conversion per session"},
    {"metric": "conversion", "segment": "All", "value": 1.4021, "unit": "pct", "period": "current", "basis": "per_user", "label": "conversion per user"},
    {"metric": "conversion", "segment": "All", "value": -0.1183, "unit": "pp", "period": "wow", "basis": "per_session", "label": "conversion wow (pp)"},
    {"metric": "conversion", "segment": "All", "value": -9.94, "unit": "pct", "period": "wow", "basis": "per_session", "label": "conversion wow (%)"},
    {"metric": "rpv", "segment": "All", "value": 4.62, "unit": "eur", "period": "current", "basis": "gross", "label": "RPV gross"},
    {"metric": "rpv", "segment": "All", "value": 4.38, "unit": "eur", "period": "current", "basis": "net", "label": "RPV net"},
    {"metric": "payment_step", "segment": "mobile / Safari iOS", "value": 63.8, "unit": "pct", "period": "current", "basis": None, "label": "payment step"},
    {"metric": "payment_step", "segment": "mobile / Safari iOS", "value": 82.6, "unit": "pct", "period": "expected", "basis": None, "label": "expected payment step"},
    {"metric": "payment_step", "segment": "mobile / Safari iOS", "value": -22.7, "unit": "pct", "period": "vs_expected", "basis": None, "label": "payment step vs expected"},
]}

GOOD = ("Week of 16 Mar 2026: 62,483 sessions (-0.3% week on week, +8.1% vs the same week last year). "
        "Conversion per session was 1.07% (-0.12 pp week on week, -9.9% week on week); per user it was 1.40%. "
        "Revenue per visit was €4.62 gross and €4.38 net of returns. "
        "The payment step on mobile / Safari iOS ran at 63.8% against an expected 82.6% (-22.7% vs expected), "
        "after the 2026-03-10 release; the trial lasts 100 nights.")


def errors(text):
    return [f.error for f in cn.check(text, SHEET).errors()]


def test_correct_note_passes():
    rep = cn.check(GOOD, SHEET)
    assert rep.passed, rep.text()
    assert len(rep.findings) == 12  # dates, the year and "100 nights" are not checked as figures


@pytest.mark.parametrize("bad, expected_error", [
    # percentage points written as a percentage
    ("Conversion per session fell 0.12% week on week.", "pp_vs_pct"),
    # relative change written as points
    ("Conversion per session fell 9.94 pp week on week.", "pp_vs_pct"),
    # wrong reference week: the year-on-year change presented as week on week
    ("Sessions rose 8.1% week on week.", "wrong_period"),
    # the expected value presented as the observed one
    ("The payment step on mobile / Safari iOS was 82.6%.", "wrong_period"),
    # conversion per session presented as per user
    ("Conversion per user was 1.07%.", "per_session_vs_per_user"),
    # gross revenue per visit presented as net of returns
    ("Revenue per visit net of returns was €4.62.", "gross_vs_net"),
    # opposite direction
    ("Sessions rose 0.32% week on week.", "sign"),
    # a number the data does not contain
    ("Conversion per session was 1.25%.", "not_in_data"),
])
def test_traps_are_rejected(bad, expected_error):
    errs = errors(bad)
    assert expected_error in errs, f"{bad!r} -> {errs}"


def test_one_wrong_number_rejects_the_whole_note():
    assert not cn.check(GOOD + " Conversion per user was 1.07%.", SHEET).passed
