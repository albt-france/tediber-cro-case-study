"""Results that need Python (statistics), written to data/processed/ for the notebook, Excel, dashboard and PDF.

- experiment_readout.csv : every test read with SRM, z tests, bootstrap of (net) revenue per visitor, decision
- power_plan.csv         : sample size and duration planned for each test (before launch)
- peeking.csv            : false-positive rate when an A/A test is checked every day vs once at the end
- business_impact.csv    : annualised impact of the shipped tests, as a range (SIMULATED store)
- detection_scorecard.csv: how the weekly monitoring handled the 8 planted events (needs data/_hidden_truth.csv;
                           the scorecard is kept, the hidden file is not committed)

    python src/analyse.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

import stats_tests as st

ROOT = Path(__file__).resolve().parents[1]
PROC, SIM = ROOT / "data" / "processed", ROOT / "data" / "sim"
TRUTH = ROOT / "data" / "_hidden_truth.csv"

# planned before launch: baseline (from the weeks before the test) and minimum detectable effect
PLAN = {"A": ("add-to-cart rate", 0.090, 0.07, 3100), "B": ("conversion rate", 0.020, 0.12, 4600),
        "C": ("conversion rate", 0.016, 0.16, 1800), "D": ("conversion rate", 0.016, 0.08, 6000)}


def readouts() -> pd.DataFrame:
    s = pd.read_csv(PROC / "experiment_summary.csv")
    o = pd.read_parquet(SIM / "experiment_orders.parquet")
    rows = []
    for t in sorted(s["test_id"].unique()):
        r = st.read_test(s, o, t)
        primary = "add_to_cart" if t == "A" else "conversion"
        rows.append({
            "test_id": t, "test_name": r["test_name"], "primary_kpi": PLAN[t][0],
            "visitors_control": r["visitors_a"], "visitors_variant": r["visitors_b"],
            "variant_share": r["srm"]["share_b"], "srm_chi2": r["srm"]["chi2"], "srm_p_value": r["srm"]["p_value"],
            "srm": r["srm"]["srm"],
            "primary_control": r[primary]["rate_a"], "primary_variant": r[primary]["rate_b"],
            "primary_lift": r[primary]["lift"], "primary_ci_low": r[primary]["ci_lift_low"],
            "primary_ci_high": r[primary]["ci_lift_high"], "primary_p_value": r[primary]["p_value"],
            "conversion_lift": r["conversion"]["lift"], "conversion_p_value": r["conversion"]["p_value"],
            "rpv_gross_control": r["rpv_gross"]["rpv_a"], "rpv_gross_variant": r["rpv_gross"]["rpv_b"],
            "rpv_gross_lift": r["rpv_gross"]["lift"], "rpv_gross_ci_low": r["rpv_gross"]["ci_low"],
            "rpv_gross_ci_high": r["rpv_gross"]["ci_high"],
            "rpv_net_control": r["rpv_net"]["rpv_a"], "rpv_net_variant": r["rpv_net"]["rpv_b"],
            "rpv_net_lift": r["rpv_net"]["lift"], "rpv_net_ci_low": r["rpv_net"]["ci_low"],
            "rpv_net_ci_high": r["rpv_net"]["ci_high"], "rpv_net_p_value": r["rpv_net"]["p_value"],
            "return_rate_control": r["return_rate_a"], "return_rate_variant": r["return_rate_b"],
            "return_rate_p_value": r["returns"]["p_value"], "decision": r["decision"]})
    return pd.DataFrame(rows)


def power_plan() -> pd.DataFrame:
    s = pd.read_csv(PROC / "experiment_summary.csv").groupby("test_id").agg(
        start=("start_date", "min"), end=("end_date", "max"), visitors=("visitors", "sum"))
    rows = []
    for t, (kpi, base, mde, per_day) in PLAN.items():
        n = st.sample_size_per_arm(base, mde)
        days = int(np.ceil(2 * n / per_day / 7) * 7)  # whole weeks, so every weekday is covered equally
        ran = (pd.Timestamp(s.loc[t, "end"]) - pd.Timestamp(s.loc[t, "start"])).days + 1
        rows.append({"test_id": t, "primary_kpi": kpi, "baseline": base, "mde_relative": mde, "alpha": 0.05,
                     "power": 0.80, "visitors_per_arm_needed": n, "eligible_visitors_per_day": per_day,
                     "planned_days": max(days, 14), "days_run": ran, "visitors_observed": int(s.loc[t, "visitors"])})
    return pd.DataFrame(rows)


def peeking() -> pd.DataFrame:
    r = st.peeking_false_positive_rate()
    return pd.DataFrame({"day": range(1, len(r["by_day"]) + 1), "false_positive_if_stopped_at_first_win": r["by_day"],
                         "false_positive_fixed_horizon": r["fixed_horizon"]})


def business_impact(ro: pd.DataFrame) -> pd.DataFrame:
    """Annualised extra net revenue of shipped tests = eligible visitors / year x net RPV x lift (CI bounds)."""
    plan = power_plan().set_index("test_id")
    rows = []
    for _, r in ro[ro["decision"] == "ship"].iterrows():
        visitors_year = plan.loc[r["test_id"], "eligible_visitors_per_day"] * 365
        base = visitors_year * r["rpv_net_control"]
        rows.append({"test_id": r["test_id"], "test_name": r["test_name"], "eligible_visitors_per_year": visitors_year,
                     "net_rpv_control_eur": r["rpv_net_control"],
                     "impact_low_eur": base * r["rpv_net_ci_low"], "impact_central_eur": base * r["rpv_net_lift"],
                     "impact_high_eur": base * r["rpv_net_ci_high"],
                     "note": "SIMULATED store; range = 95% bootstrap interval; assumes the effect holds after launch"})
    return pd.DataFrame(rows)


def scorecard(ro: pd.DataFrame) -> pd.DataFrame:
    truth = pd.read_csv(TRUTH, parse_dates=["start_date", "end_date"])
    inc = pd.read_csv(PROC / "anomaly_incidents.csv", parse_dates=["first_day", "last_day"])
    rec = pd.read_csv(PROC / "reconciliation_incidents.csv", parse_dates=["first_day", "last_day"])
    fun = pd.read_csv(PROC / "funnel_segments.csv")

    def overlap(df, a, b):
        return df[(df["first_day"] <= b) & (df["last_day"] >= a)]

    rows = []
    for _, e in truth.iterrows():
        a, b = e["start_date"], e["end_date"]
        if e["event_id"] == 1:
            m = overlap(inc, a, b + pd.Timedelta(days=7))
            m = m[m["slice"].str.contains("Safari iOS") & (m["kpi"] == "payment step") & (m["status"] == "open: investigate")]
            found, how = len(m) > 0, "incident on mobile / Safari iOS, payment step"
            delay = (m["first_day"].min() - a).days if found else None
            cause = found and m["candidate_releases"].str.contains("Split-payment widget").any()
        elif e["event_id"] == 2:
            m = overlap(inc, a, b)
            m = m[m["slice"].str.contains("Mattress") & (m["kpi"] == "add-to-cart rate") & (m["status"] == "open: investigate")]
            found, how = len(m) > 0, "incident on mobile / Mattress, add-to-cart rate (desktop not flagged)"
            delay = (m["first_day"].min() - a).days if found else None
            cause = found and m["candidate_releases"].fillna("").str.contains("carousel").any()
        elif e["event_id"] == 3:
            c = fun[fun["dimension"] == "Category"].set_index("segment")["shipping_step_abandonment"]
            ratio = c[["Bed base & bed", "Sofa"]].mean() / c.drop(["Bed base & bed", "Sofa"]).mean()
            found, how, delay, cause = ratio >= 1.5, f"funnel by category: shipping-step abandonment x{ratio:.1f}", None, True
        elif e["event_id"] == 4:
            m = overlap(inc, a, b + pd.Timedelta(days=7))
            found = len(m) > 0 and (m["status"] == "explained: traffic mix, no incident opened").all()
            how, delay, cause = f"{len(m)} alerts, all triaged as traffic mix; no incident opened", None, True
        elif e["event_id"] == 5:
            m = overlap(rec, a, b)
            found, how = len(m) > 0, "reconciliation: analytics revenue above the shop's, duplicate purchase events"
            delay = (m["first_day"].min() - a).days if found else None
            cause = found and m["candidate_releases"].fillna("").str.contains("tag").any()
        elif e["event_id"] == 6:
            r = ro.set_index("test_id").loc["B"]
            found, how, delay, cause = bool(r["srm"]), f"SRM check: variant share {r['variant_share']:.1%}, p = {r['srm_p_value']:.1e}", None, True
        elif e["event_id"] == 7:
            r = ro.set_index("test_id").loc["D"]
            found = r["decision"] == "iterate"
            how = (f"conversion {r['conversion_lift']:+.1%} (p = {r['conversion_p_value']:.3f}) but net RPV "
                   f"{r['rpv_net_lift']:+.1%} [{r['rpv_net_ci_low']:+.1%}; {r['rpv_net_ci_high']:+.1%}]")
            delay, cause = None, True
        else:
            m = overlap(inc, a, b)
            found = (m["status"] != "open: investigate").all() if len(m) else True
            how, delay, cause = f"{len(m)} incidents opened during Black Month 2026 (baseline = last year's promo)", None, True
        rows.append({"event_id": e["event_id"], "event": e["event"], "expected_handling": e["expected_handling"],
                     "handled_correctly": bool(found), "how": how, "days_to_detect": delay,
                     "cause_found_in_release_log": bool(cause)})
    sc = pd.DataFrame(rows)
    matched = {"mobile / Safari iOS", "mobile / Mattress"}
    false_pos = inc[(inc["status"] == "open: investigate") & ~inc["slice"].isin(matched)]
    sc.loc[len(sc)] = {"event_id": 99, "event": "Other incidents opened (false positives)",
                       "expected_handling": "none", "handled_correctly": len(false_pos) == 0,
                       "how": f"{len(false_pos)} other open incidents over 18 months",
                       "days_to_detect": None, "cause_found_in_release_log": None}
    return sc


if __name__ == "__main__":
    ro = readouts()
    ro.to_csv(PROC / "experiment_readout.csv", index=False)
    power_plan().to_csv(PROC / "power_plan.csv", index=False)
    peeking().to_csv(PROC / "peeking.csv", index=False)
    business_impact(ro).to_csv(PROC / "business_impact.csv", index=False)
    if TRUTH.exists():
        sc = scorecard(ro)
        sc.to_csv(PROC / "detection_scorecard.csv", index=False)
        print(sc[["event_id", "event", "handled_correctly", "days_to_detect", "how"]].to_string(index=False))
    else:
        print("data/_hidden_truth.csv absent: detection_scorecard.csv kept as published")
    print(ro[["test_id", "decision", "primary_lift", "primary_p_value", "rpv_net_lift"]].round(4).to_string(index=False))
