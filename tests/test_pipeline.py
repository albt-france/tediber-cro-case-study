"""Checks on the published outputs: the weekly notes pass the number check, statistics behave as expected."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import stats_tests as st  # noqa: E402
import weekly_summary as ws  # noqa: E402

PROC = ROOT / "data" / "processed"


@pytest.mark.parametrize("week", ["2026-03-16", "2026-05-18", "2026-07-13", "2026-09-07", "2026-11-23"])
def test_template_note_passes_the_number_check(week):
    sheet = ws.build_facts(week)
    rep = ws.check_numbers.check(ws.template_draft(sheet), sheet)
    assert rep.passed, rep.text()


def test_sample_size_matches_textbook_value():
    # 5% baseline, +10% relative lift, alpha 5%, power 80%: about 31,200 per arm (two-sided, unpooled)
    assert 31_000 < st.sample_size_per_arm(0.05, 0.10) < 31_500


def test_srm_detects_52_48_and_accepts_50_50():
    assert st.srm_check(52_000, 48_000)["srm"]
    assert not st.srm_check(50_100, 49_900)["srm"]


def test_peeking_inflates_false_positives():
    r = st.peeking_false_positive_rate(n_sims=1000)
    assert r["fixed_horizon"] < 0.08 and r["daily_peeking"] > 0.15


def test_decisions_documented():
    ro = pd.read_csv(PROC / "experiment_readout.csv").set_index("test_id")["decision"].to_dict()
    assert ro == {"A": "ship", "B": "invalid: fix and relaunch", "C": "ship", "D": "iterate"}


def test_detection_scorecard_all_handled():
    sc = pd.read_csv(PROC / "detection_scorecard.csv")
    assert sc["handled_correctly"].all()


def test_no_visitor_ids_in_published_ga4_outputs():
    for f in PROC.glob("ga4_*.csv"):
        assert "user_pseudo_id" not in f.read_text(encoding="utf-8")
