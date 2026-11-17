"""Write the 4 A/B test briefs and 4 read-outs in docs/ab_tests/ from the planned and observed numbers
(data/processed/power_plan.csv, experiment_readout.csv, business_impact.csv). SIMULATED store.

    python src/build_test_docs.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC, OUT = ROOT / "data" / "processed", ROOT / "docs" / "ab_tests"

BRIEFS = {
    "A": dict(
        seen="Yes - the public mattress page shows a sticky price + add-to-cart bar on mobile (17 Nov 2026). This brief shows how such a feature is measured.",
        slug="sticky_add_to_cart_mobile",
        problem="In the simulated store, on mobile product pages the add-to-cart button leaves the screen as soon as the visitor scrolls "
                "through photos, sizes and reviews. Mobile add-to-cart rate is well below desktop in the weekly report.",
        saw="mobile visitors scroll long product pages and add to cart less often than desktop visitors",
        believe="keeping the add-to-cart button visible (sticky bar with price and size)",
        cause="more mobile visitors to add a mattress or pillow to the cart",
        kpi="add-to-cart rate per visitor (mobile product-page visitors)",
        guardrails="conversion rate per visitor, net revenue per visitor, 100-night return rate, page speed (LCP)",
        variants="Control: current page. Variant: sticky bottom bar (price + selected size + 'Ajouter au panier') once "
                 "the main button scrolls out of view.",
        population="mobile visitors who view a product page", split="50/50, by visitor (cookie)",
        risks="Bar hiding the chat or cookie banner; double tap on the button; layout shift (CLS)."),
    "B": dict(
        seen="Yes - trial and free returns are listed right under the button on the public mattress page (17 Nov 2026).",
        slug="trial_reassurance_near_button",
        problem="In the simulated store, the 100-night trial and free return appear far from the add-to-cart button "
                "on product pages.",
        saw="the trial promise is shown in the header banner and lower on the page, not next to the button",
        believe="a short '100 nuits d'essai, retour gratuit' line right under the button",
        cause="more product-page visitors to order",
        kpi="conversion rate per visitor (product-page visitors)",
        guardrails="100-night return rate, net revenue per visitor, add-to-cart rate",
        variants="Control: current page. Variant: one line with icon under the button, linking to the trial page.",
        population="visitors who view a product page", split="50/50, by visitor",
        risks="Variant built as a redirect to a copy of the page (first run): any redirect must be avoided or "
              "checked for SRM daily."),
    "C": dict(
        seen="Yes - the public bed-base page shows the delivery options and the room-delivery fee (17 Nov 2026). The simulated store starts without it.",
        slug="bulky_delivery_fee_on_product_page",
        problem="In the simulated store, delivery of bed bases, beds and sofas to the room is paid and the fee becomes "
                "visible only at the delivery step. Abandonment at that step is twice as high as for other categories.",
        saw="shipping-step abandonment of about 40% for bulky items vs about 20% for the other categories",
        believe="showing the delivery fee and options on the product page, before the cart",
        cause="fewer bulky-item shoppers to abandon at the delivery step",
        kpi="conversion rate per visitor (bulky-item product-page visitors)",
        guardrails="add-to-cart rate (expected to fall a little: informed visitors), net revenue per visitor, "
                   "average order value",
        variants="Control: current page. Variant: 'Livraison dans la pièce de votre choix : XX EUR, sous 8 à 10 jours' "
                 "block under the price, with a link to the delivery page.",
        population="visitors who view a bed base, bed or sofa product page", split="50/50, by visitor",
        risks="Fee shown must match the checkout exactly (QA on 3 postcodes); add-to-cart may fall (not a failure)."),
    "D": dict(
        seen="Yes - the public mattress pages show a comparator and a 'Quel matelas choisir ?' quiz (17 Nov 2026). Its effect on returns is not observable from outside.",
        slug="mattress_comparator",
        problem="In the simulated store, several mattress models with different firmness and prices: visitors open several product pages "
                "and come back several times before choosing.",
        saw="multi-session journeys and a high share of mattress returns within the 100 nights",
        believe="a side-by-side comparator (firmness, height, materials, price) reachable from every mattress page",
        cause="more visitors to choose a mattress and order",
        kpi="conversion rate per visitor (all visitors)",
        guardrails="100-night return rate (mattresses), net revenue per visitor after returns, average order value",
        variants="Control: no comparator. Variant: 'Comparer nos matelas' table in the menu and on mattress pages.",
        population="all visitors", split="50/50, by visitor",
        risks="Easier choice may also mean a wrong choice (returns): read on net revenue, wait for returns to mature."),
}
QA = """## Pre-launch QA checklist
- [ ] Hypothesis, primary KPI, guardrails, sample size and duration written **before** launch (this brief)
- [ ] Variant renders on iOS Safari, Android Chrome, desktop Chrome/Safari/Edge; no layout shift (CLS) added
- [ ] Variant is served client-side, **no redirect** (redirects lose visitors and create a sample ratio mismatch)
- [ ] Assignment is by visitor and sticky across sessions; returning visitors keep their variant
- [ ] Test-tool events reach analytics (exposure event + variant id); purchases de-duplicated on transaction id
- [ ] A/A or 24 h smoke check: allocation 50/50 (SRM chi-square p > 0.001), no error spike, page speed unchanged
- [ ] No other test on the same pages and audience; no promotion starting during the test window
- [ ] Owner, launch date, end date and decision meeting in the test log
"""


def fp(p):
    return "< 0.0001" if p < 1e-4 else f"{p:.4f}"


def pct(x, d=1):
    return f"{x:+.{d}%}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plan = pd.read_csv(PROC / "power_plan.csv").set_index("test_id")
    ro = pd.read_csv(PROC / "experiment_readout.csv").set_index("test_id")
    imp = pd.read_csv(PROC / "business_impact.csv").set_index("test_id")
    summ = pd.read_csv(PROC / "experiment_summary.csv").groupby("test_id").agg(start=("start_date", "min"), end=("end_date", "max"))
    for t, b in BRIEFS.items():
        p, r = plan.loc[t], ro.loc[t]
        brief = f"""# Test {t} brief - {r['test_name']}
*SIMULATED store modelled on public information (its numbers are not Tediber's). Template usable as is.*

**Already on Tediber's public pages?** {b['seen']}

| Field | Content |
|---|---|
| Problem | {b['problem']} |
| Hypothesis | **Because we saw** {b['saw']}, **we believe** {b['believe']} **will cause** {b['cause']}, **measured by** the {p['primary_kpi']}. |
| Variants | {b['variants']} |
| Population / split | {b['population']}; {b['split']} |
| Primary KPI | {b['kpi']} |
| Guardrails | {b['guardrails']} |
| Baseline / MDE | {p['baseline']:.1%} / {p['mde_relative']:.0%} relative (alpha 5%, power 80%, two-sided) |
| Sample size | {p['visitors_per_arm_needed']:,} visitors per variant ({2 * p['visitors_per_arm_needed']:,} in total) |
| Duration | {p['planned_days']} days at ~{p['eligible_visitors_per_day']:,} eligible visitors/day (whole weeks) - fixed in advance, no early stop |
| Planned dates | {summ.loc[t, 'start']} to {summ.loc[t, 'end']} |
| Decision rule | SRM -> invalid; primary up (p < 0.05) and no guardrail breached -> ship; primary up but a guardrail breached -> iterate; otherwise drop |
| Risks | {b['risks']} |

{QA}"""
        (OUT / f"test_{t}_{b['slug']}_brief.md").write_text(brief, encoding="utf-8")

        srm = (f"Variant share {r['variant_share']:.2%} (chi-square {r['srm_chi2']:.1f}, p = {r['srm_p_value']:.1e}) -> "
               + ("**SAMPLE RATIO MISMATCH: the test is not read.**" if r["srm"] else "allocation OK."))
        if r["srm"]:
            body = (f"The variant was served by a redirect to a copy of the page. Some visitors never reached it "
                    f"(slow redirect, bots filtered differently, back button), so the two groups are no longer comparable: "
                    f"any difference could come from who was lost, not from the change. The numbers below are shown "
                    f"only to explain why they must not be used: conversion {pct(r['primary_lift'])} "
                    f"(p = {r['primary_p_value']:.2f}).\n\n**Decision: {r['decision']}.** Rebuild the variant client-side, "
                    f"run a 48 h allocation check, relaunch for the full planned duration.")
            learn = "Check allocation on day 1 and every day; a redirect is a red flag in the QA checklist."
        else:
            body = (f"| Metric | Control | Variant | Lift [95% CI] | p-value |\n|---|---|---|---|---|\n"
                    f"| {r['primary_kpi']} (primary) | {r['primary_control']:.2%} | {r['primary_variant']:.2%} | "
                    f"{pct(r['primary_lift'])} [{pct(r['primary_ci_low'])}; {pct(r['primary_ci_high'])}] | {fp(r['primary_p_value'])} |\n"
                    f"| Revenue per visitor (gross) | EUR {r['rpv_gross_control']:.2f} | EUR {r['rpv_gross_variant']:.2f} | "
                    f"{pct(r['rpv_gross_lift'])} [{pct(r['rpv_gross_ci_low'])}; {pct(r['rpv_gross_ci_high'])}] | bootstrap |\n"
                    f"| Revenue per visitor (net of returns) | EUR {r['rpv_net_control']:.2f} | EUR {r['rpv_net_variant']:.2f} | "
                    f"{pct(r['rpv_net_lift'])} [{pct(r['rpv_net_ci_low'])}; {pct(r['rpv_net_ci_high'])}] | {r['rpv_net_p_value']:.2f} |\n"
                    f"| 100-night return rate (guardrail) | {r['return_rate_control']:.1%} | {r['return_rate_variant']:.1%} | | "
                    f"{fp(r['return_rate_p_value'])} |\n")
            if t == "A":
                body += f"| Conversion rate (secondary) | | | {pct(r['conversion_lift'])} | {r['conversion_p_value']:.2f} |\n"
            body += f"\n**Decision: {r['decision'].upper()}.** "
            if t in imp.index:
                i = imp.loc[t]
                body += (f"Annualised effect on net revenue if the lift holds: EUR {i['impact_central_eur'] / 1e6:.1f} M "
                         f"(95% range EUR {i['impact_low_eur'] / 1e6:.1f} M to {i['impact_high_eur'] / 1e6:.1f} M) - "
                         f"SIMULATED store; the range, not the central value, is what we commit to.")
            learn = {"A": "The primary metric moved clearly; revenue per visitor is too noisy to read at this sample size, "
                          "so the decision rests on the primary metric plus guardrails not breached. Follow conversion after launch.",
                     "C": "Showing a cost early lowers add-to-cart a little but removes the bad surprise at checkout: "
                          "judge the full funnel, not one step. The test ran while the purchase tag was duplicated in "
                          "analytics; it was read from the testing tool and the back office, so it is not affected.",
                     "D": "A higher conversion is not a win if returns rise: the comparator helps people decide but not "
                          "always choose the right firmness. Next: add a firmness guide / sleep-position question, "
                          "re-test with net revenue per visitor as the primary metric, after returns have matured."}[t]
        rep = f"""# Test {t} read-out - {r['test_name']}
*SIMULATED store. Ran {summ.loc[t, 'start']} to {summ.loc[t, 'end']}; {r['visitors_control']:,} control and {r['visitors_variant']:,} variant visitors.*

**1. Allocation check (first).** {srm}

**2. Results.**

{body}

**3. Learning.** {learn}

*Read with `src/stats_tests.py` (z test on proportions, bootstrap of revenue per visitor, chi-square SRM). Returns observed up to 30 Nov 2026.*
"""
        (OUT / f"test_{t}_{b['slug']}_readout.md").write_text(rep, encoding="utf-8")
    print("written", len(BRIEFS) * 2, "files in docs/ab_tests/")


if __name__ == "__main__":
    main()
