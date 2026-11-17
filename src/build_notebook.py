"""Build and execute notebooks/cro_analysis.ipynb (the single analysis notebook).

    python src/build_notebook.py
"""
from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "cro_analysis.ipynb"

CELLS = [
    ("md", """# CRO analysis - DTC bedding store (case study)
Real public data where it exists (**PUBLIC DATA**), a simulated store modelled on public information where it does not
(**SIMULATED** - never Tediber's numbers). Every table below is produced by `sql/` (DuckDB) or `src/` and saved in
`data/processed/`. Run order: `extract_ga4.py` -> `simulate.py` -> `run_sql.py` -> `analyse.py` -> this notebook."""),
    ("code", """import sys, pandas as pd, numpy as np
sys.path.insert(0, '../src')
import stats_tests as st
P = '../data/processed/'
pd.set_option('display.width', 160); pd.set_option('display.max_columns', 20)
pct = lambda s: (100 * s).round(2)"""),
    ("md", """## 1. Real funnel (PUBLIC DATA - Google Merchandise Store GA4 sample, not Tediber)
Open funnel: share of sessions reaching each step. Sessions = `user_pseudo_id` + `ga_session_id` (the id alone is not unique)."""),
    ("code", """g = pd.read_csv(P + 'ga4_funnel_segments.csv')
cols = ['sessions', 'view_item', 'add_to_cart', 'begin_checkout', 'add_shipping_info', 'add_payment_info', 'purchase']
show = g[g.dimension.isin(['All', 'Device', 'Visitor type', 'Landing page'])].set_index(['dimension', 'segment'])
(show[cols[1:]].div(show.sessions, axis=0) * 100).round(2)"""),
    ("md", """Returning visitors convert 4.6x better than new ones (3.11% vs 0.68%): for a product bought after several visits,
conversion **per user** over a period says more than conversion per session. Mobile and desktop are close in this sample."""),
    ("code", """pd.read_csv(P + 'ga4_data_quality.csv').assign(value=lambda d: d.value.round(4))"""),
    ("code", """pd.read_csv(P + 'ga4_revenue_dedup.csv')"""),
    ("md", """**Data quality on a real export**: 326 transaction ids are sent more than once (+7.4% revenue if not de-duplicated),
906 purchase events have no usable id, and a fifth of sessions have no channel. These checks come before any funnel reading."""),
    ("md", "## 2. Weekly report (SIMULATED)"),
    ("code", """k = pd.read_csv(P + 'weekly_kpis.csv', parse_dates=['week_start'])
a = k[k.dimension == 'All'].set_index('week_start')
a.loc['2026-03-02':'2026-03-23', ['sessions', 'conversion_rate', 'conversion_per_user', 'aov_eur', 'revenue_per_visit_eur',
                                   'net_revenue_per_visit_eur', 'add_to_cart_rate', 'checkout_abandonment', 'conversion_rate_wow']].round(4)"""),
    ("md", """The topline barely moves in the week of 16 March (conversion -1% week on week). The problem is hidden in one segment:"""),
    ("code", """f = pd.read_csv(P + 'funnel_segments.csv')
f[f.dimension.isin(['Device x browser', 'Category'])].set_index(['dimension', 'segment'])[
    ['sessions', 'pass_add_to_cart', 'pass_checkout', 'pass_shipping', 'pass_payment', 'conversion_rate']].round(4)"""),
    ("md", """Over the whole period, **bulky items (bed bases, beds, sofas) lose twice as many shoppers at the delivery step**
(~40% vs ~20%): a structural leak, not an incident - it goes to the backlog (test C)."""),
    ("md", """## 3. Anomaly detection and how it scored (SIMULATED)
Method (`sql/03_anomalies.sql`): 7-day trailing rate per slice and KPI; expected = median of the same weekday over 8 weeks,
promotion windows excluded (inside a promotion: last year's promotion, scaled); robust z with a MAD / binomial floor;
alert = |z| >= 3.5, change >= 10%, for 5 days or more. Then a traffic-mix check and the release log."""),
    ("code", """inc = pd.read_csv(P + 'anomaly_incidents.csv')
inc[['slice', 'kpi', 'first_day', 'last_day', 'days_flagged', 'rel_change_at_peak', 'z_at_peak', 'status']].round(3)"""),
    ("code", """pd.read_csv(P + 'mix_decomposition.csv').round(5)"""),
    ("md", """Early September: topline conversion falls, yet inside each channel it is flat (rate effects ~0); the fall is the
**mix effect** of four times more paid-social sessions. Correct handling: explain it, open no incident."""),
    ("code", """pd.read_csv(P + 'reconciliation_incidents.csv')"""),
    ("code", """sc = pd.read_csv(P + 'detection_scorecard.csv')
sc[['event_id', 'event', 'expected_handling', 'handled_correctly', 'days_to_detect', 'how']]"""),
    ("md", """All 8 planted events are handled as they should be (the answer key was hidden during the analysis and used only here):
the two real breaks are found 2 and 5 days after they start and linked to the right release, the duplicate purchases the day
after, the mix effect and Black Month raise no incident, and no other incident is opened in 18 months."""),
    ("md", "## 4. Testing it right (SIMULATED)\n### Sample size and duration, decided before launch"),
    ("code", """pd.read_csv(P + 'power_plan.csv')"""),
    ("code", """# the same calculation by hand for test D: 1.6% baseline, +8% relative MDE
st.sample_size_per_arm(0.016, 0.08), st.mde_for_sample(0.016, 168_000)"""),
    ("md", "### Peeking: an A/A test checked every day"),
    ("code", """pk = st.peeking_false_positive_rate()
print(f"read once at the end: {pk['fixed_horizon']:.1%} false positives; stop at the first p < 0.05: {pk['daily_peeking']:.1%}")"""),
    ("md", "### Read-outs: SRM first, then the primary KPI, then guardrails"),
    ("code", """ro = pd.read_csv(P + 'experiment_readout.csv')
ro[['test_id', 'variant_share', 'srm_p_value', 'primary_kpi', 'primary_lift', 'primary_ci_low', 'primary_ci_high', 'primary_p_value',
    'rpv_net_lift', 'rpv_net_ci_low', 'rpv_net_ci_high', 'return_rate_control', 'return_rate_variant', 'decision']].round(4)"""),
    ("code", """# recompute test D by hand from the counts (z test) to check the table
s = pd.read_csv(P + 'experiment_summary.csv').set_index(['test_id', 'variant'])
c, v = s.loc[('D', 'control')], s.loc[('D', 'variant')]
st.two_proportion_test(int(c.orders), int(c.visitors), int(v.orders), int(v.visitors))"""),
    ("md", """**Test D, "the winner that loses"**: conversion +8% (p = 0.004) but 100-night returns go from 7.6% to 10.9%, so net
revenue per visitor is +2.9% with an interval from -3.4% to +9.6%: not shown to be better. Decision: iterate (add firmness
guidance, re-test on net revenue). **Test B** is not read at all: 48/52 split, chi-square p < 0.001 (a redirect lost visitors)."""),
    ("md", "## 5. Business impact, as a range"),
    ("code", """pd.read_csv(P + 'business_impact.csv').round(0)"""),
    ("md", """Annualised net revenue of the shipped tests on the simulated store, from the 95% bootstrap interval. Test A's range
includes zero on revenue (its primary metric, add-to-cart, is clearly up): we commit to the range, not to the central value,
and follow conversion after launch."""),
]


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(s) if t == "md" else nbf.v4.new_code_cell(s) for t, s in CELLS]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(NB.parent)}})
    NB.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NB)
    print(f"written and executed {NB.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
