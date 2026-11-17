"""Matplotlib charts for the PDF report (report/img/*.png). Every number is read from data/processed or data/sim.

Style: grey-beige page, white cards, blue for the data, grey for comparison, red for alerts, dashed lines for
thresholds and expected values, Segoe UI. Each chart says in its title whether it is PUBLIC DATA or SIMULATED.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC, SIM, IMG = ROOT / "data" / "processed", ROOT / "data" / "sim", ROOT / "report" / "img"
BLUE, GREY, RED, GREEN, INK, MUTED, GRID = "#2A78D6", "#A3A19A", "#D03B3B", "#2E8B57", "#0B0B0B", "#52514E", "#E1E0D9"
LIGHT = "#C9DDF5"

plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False,
    "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlecolor": INK, "axes.titlelocation": "left",
})
PCT = mtick.PercentFormatter(1.0)


def csv(name):
    return pd.read_csv(PROC / f"{name}.csv")


def save(fig, name):
    IMG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(IMG / f"{name}.png", dpi=200)
    plt.close(fig)
    return f"img/{name}.png"


def shade_promos(ax, a=None, b=None):
    pr = pd.read_parquet(SIM / "promo_calendar.parquet")
    for r in pr.itertuples():
        ax.axvspan(r.start_date, r.end_date, color=GREY, alpha=0.13, lw=0)


def months(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))


# ------------------------------------------------------------------ page 1: company and market
def market():
    m = csv("market_eurostat")
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    for ind, ls, lab in (("I_BUY3", "-", "bought online, last 3 months"), ("I_BFURN1", "--", "bought furniture / home goods online")):
        for geo, col in (("FR", BLUE), ("EU27_2020", GREY)):
            d = m[(m.indicator == ind) & (m.geo == geo)].sort_values("year")
            ax.plot(d.year, d.pct_individuals / 100, ls, color=col, marker="o", ms=3.5, lw=1.8,
                    label=f"{'France' if geo == 'FR' else 'EU-27'} - {lab}")
            last = d.iloc[-1]
            ax.annotate(f"{last.pct_individuals:.1f}%", (last.year, last.pct_individuals / 100), xytext=(4, 0),
                        textcoords="offset points", va="center", fontsize=8.5, color=col)
    ax.yaxis.set_major_formatter(PCT)
    ax.set_ylim(0, 0.8)
    ax.set_title("Share of individuals buying online (PUBLIC DATA, Eurostat)")
    ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(0, 0.55))
    return save(fig, "market")


def catalogue():
    c = csv("tediber_catalogue_by_category").sort_values("product_urls")
    c = c[c.category != "other"]
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    ax.barh(c.category, c.product_urls, color=BLUE)
    for y, v in enumerate(c.product_urls):
        ax.text(v + 1.5, y, str(v), va="center", fontsize=8.5, color=MUTED)
    ax.set_title(f"Product URLs by category ({c.product_urls.sum() + 1} in total)\nPUBLIC DATA - sitemap, 17 Nov 2026")
    ax.grid(axis="y", visible=False)
    return save(fig, "catalogue")


def prices():
    p = csv("tediber_prices").dropna(subset=["min_price_eur"]).sort_values("max_price_eur")
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    for y, r in enumerate(p.itertuples()):
        ax.plot([r.min_price_eur, r.max_price_eur], [y, y], color=LIGHT, lw=5, solid_capstyle="round")
        ax.plot([r.min_price_eur, r.max_price_eur], [y, y], "o", color=BLUE, ms=4)
    ax.set_yticks(range(len(p)), [h.replace("-", " ") for h in p.handle], fontsize=8.5)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"€{x:,.0f}"))
    ax.set_title("Price range by product (sizes / options)\nPUBLIC DATA - product pages, 17 Nov 2026")
    ax.grid(axis="y", visible=False)
    return save(fig, "prices")


# ------------------------------------------------------------------ page 2: page speed
def lighthouse():
    lh = csv("lighthouse_summary")
    order = ["home", "cat_mattress", "cat_bedbase", "pdp_mattress", "pdp_bedbase", "pdp_duvet"]
    names = {"home": "Homepage", "cat_mattress": "Category: mattresses", "cat_bedbase": "Category: bed bases",
             "pdp_mattress": "Product: mattress", "pdp_bedbase": "Product: bed base", "pdp_duvet": "Product: duvet"}
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.3))
    for ax, ff in zip(axes, ("mobile", "desktop")):
        d = lh[lh.form_factor == ff].set_index("page").reindex(order)
        ax.barh([names[i] for i in order], d.lcp_s, color=BLUE if ff == "mobile" else GREY)
        ax.axvline(2.5, color=RED, ls="--", lw=1)
        ax.text(2.6, -0.6, "2.5 s 'good' threshold", color=RED, fontsize=8)
        for y, v in enumerate(d.lcp_s):
            ax.text(v + 0.2, y, f"{v:.1f} s", va="center", fontsize=8.5, color=MUTED)
        ax.invert_yaxis()
        ax.set_title(f"LCP {ff} (lab, median of 3)")
        ax.grid(axis="y", visible=False)
        if ff == "desktop":
            ax.set_yticklabels([])
    fig.suptitle("PUBLIC DATA - Lighthouse 12.8 lab runs on public pages, 17 Nov 2026 (simulated slow-4G mobile)", x=0.01,
                 ha="left", fontsize=9, color=MUTED, y=0.02)
    return save(fig, "lighthouse")


def lighthouse_weight():
    lh = csv("lighthouse_summary")
    d = lh[lh.form_factor == "mobile"].set_index("page")
    order = ["home", "cat_mattress", "cat_bedbase", "pdp_mattress", "pdp_bedbase", "pdp_duvet"]
    short = ["Home", "Cat. mattr.", "Cat. bed b.", "PDP mattr.", "PDP bed b.", "PDP duvet"]
    fig, ax = plt.subplots(figsize=(4.4, 3.3))
    ax.bar(short, d.reindex(order).tbt_ms, color=BLUE)
    ax.axhline(200, color=RED, ls="--", lw=1)
    ax.text(5.4, 230, "200 ms", color=RED, fontsize=8, ha="right")
    ax.set_title("Total Blocking Time, mobile (lab, ms)\nscripts keep the main thread busy")
    ax.tick_params(axis="x", labelsize=8, rotation=30)
    ax.grid(axis="x", visible=False)
    return save(fig, "lighthouse_tbt")


# ------------------------------------------------------------------ page 3: real GA4 funnel
GA4_STEPS = [("sessions", "Session"), ("view_item", "View item"), ("add_to_cart", "Add to cart"),
             ("begin_checkout", "Checkout"), ("add_shipping_info", "Shipping"), ("add_payment_info", "Payment"),
             ("purchase", "Purchase")]


def ga4_funnel():
    g = csv("ga4_funnel_segments")
    a = g[g.dimension == "All"].iloc[0]
    vals = [a[k] for k, _ in GA4_STEPS]
    fig, ax = plt.subplots(figsize=(6.0, 3.3))
    ax.bar([l for _, l in GA4_STEPS], vals, color=BLUE)
    for i in range(1, len(vals)):
        ax.text(i, vals[i] * 1.15, f"{vals[i] / vals[i - 1]:.0%}", ha="center", fontsize=8.5, color=INK)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_title("Real funnel: sessions reaching each step (log scale), step pass rate on top\n"
                 "PUBLIC DATA - Google Merchandise Store GA4 sample, Nov 2020 - Jan 2021 (not Tediber)")
    ax.grid(axis="x", visible=False)
    return save(fig, "ga4_funnel")


def ga4_segments():
    g = csv("ga4_funnel_segments")
    rows = [("Device", "desktop"), ("Device", "mobile"), ("Visitor type", "New"), ("Visitor type", "Returning"),
            ("Landing page", "Home"), ("Landing page", "Product page"), ("First-user channel", "Organic search"),
            ("First-user channel", "Paid search"), ("First-user channel", "Referral")]
    d = pd.concat([g[(g.dimension == a) & (g.segment == b)] for a, b in rows])
    fig, ax = plt.subplots(figsize=(4.8, 3.3))
    lab = [f"{s}" for s in d.segment]
    cols = [GREY if s in ("desktop", "mobile") else BLUE for s in d.segment]
    ax.barh(lab, d.conversion_rate, color=cols)
    for y, v in enumerate(d.conversion_rate):
        ax.text(v + 0.0005, y, f"{v:.2%}", va="center", fontsize=8.5, color=MUTED)
    ax.axvline(g[g.dimension == "All"].conversion_rate.iloc[0], color=INK, ls="--", lw=0.8)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(PCT)
    ax.set_title("Conversion per session by segment (PUBLIC DATA)\ndashed = all sessions")
    ax.grid(axis="y", visible=False)
    return save(fig, "ga4_segments")


# ------------------------------------------------------------------ page 4: weekly monitoring
def weekly_topline():
    k = csv("weekly_kpis")
    a = k[k.dimension == "All"].copy()
    a["week_start"] = pd.to_datetime(a.week_start)
    ch = k[k.dimension == "Channel"].copy()
    ch["week_start"] = pd.to_datetime(ch.week_start)
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    shade_promos(ax)
    for seg, col in (("Organic search", GREY), ("Paid social", GREY)):
        d = ch[ch.segment == seg]
        ax.plot(d.week_start, d.conversion_rate, color=col, lw=1, ls=":" if seg == "Paid social" else "-")
        ax.text(d.week_start.iloc[-1], d.conversion_rate.iloc[-1], f" {seg}", fontsize=8, color=MUTED, va="center")
    ax.plot(a.week_start, a.conversion_rate, color=BLUE, lw=2, label="all traffic")
    ax.axvspan(pd.Timestamp("2026-08-31"), pd.Timestamp("2026-09-13"), color=RED, alpha=0.12, lw=0)
    mx = csv("mix_decomposition")
    drop = mx.topline_cr_during.iloc[0] / mx.topline_cr_before.iloc[0] - 1
    ax.annotate(f"early Sep: topline {drop:+.0%} vs the 4 weeks before;\nmore paid-social visits, channels stable\n-> mix effect, no incident",
                (pd.Timestamp("2026-09-07"), 0.0094), xytext=(pd.Timestamp("2025-11-20"), 0.0052), fontsize=8.5, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.8))
    ax.text(pd.Timestamp("2026-10-25"), 0.0160, "Black Month: up, as in 2025 -> no alert", fontsize=8.5, color=MUTED, ha="right")
    ax.set_ylim(0.002, 0.0172)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=1))
    months(ax)
    ax.set_title("Weekly conversion per session (SIMULATED) - grey bands = promotions")
    return save(fig, "weekly_topline")


def mix_bars():
    m = csv("mix_decomposition")
    m = m[m.first_day == m.first_day.min()]
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    x = np.arange(len(m))
    ax.bar(x - 0.2, m.rate_effect * 100, 0.4, color=BLUE, label="rate effect (inside the channel)")
    ax.bar(x + 0.2, m.mix_effect * 100, 0.4, color=RED, label="mix effect (channel weight)")
    ax.set_xticks(x, [c.replace(" / ", "/\n").replace(" ", "\n") for c in m.channel], fontsize=8)
    ax.axhline(0, color=INK, lw=0.6)
    tot_r, tot_m = m.rate_effect.sum() * 100, m.mix_effect.sum() * 100
    ax.set_title(f"Why conversion fell in early Sep (SIMULATED)\nrate {tot_r:+.2f} pp, mix {tot_m:+.2f} pp")
    ax.set_ylabel("pp of topline conversion")
    ax.legend(fontsize=8, loc="upper left")
    ax.set_ylim(top=max(m.mix_effect.max(), m.rate_effect.max()) * 100 * 1.9)
    ax.grid(axis="x", visible=False)
    return save(fig, "mix")


def reconciliation():
    r = csv("reconciliation_daily")
    r["d"] = pd.to_datetime(r.d)
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    ax.plot(r.d, r.revenue_ratio_7d, color=BLUE, lw=1.6)
    ax.axhline(1, color=RED, ls="--", lw=1)
    ax.axvspan(pd.Timestamp("2026-07-07"), pd.Timestamp("2026-08-03"), color=RED, alpha=0.1, lw=0)
    ax.text(pd.Timestamp("2026-06-25"), 1.075, "tag migrated 7 Jul,\nfixed 4 Aug", fontsize=8.5, color=RED, ha="right")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))
    months(ax)
    ax.set_title("Analytics revenue / shop revenue, 7 days (SIMULATED)\n> 100% = purchases counted twice")
    return save(fig, "reconciliation")


# ------------------------------------------------------------------ page 5: leak -> cause
def safari():
    a = csv("anomaly_series")
    a["d"] = pd.to_datetime(a.d)
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    win = (a.d >= "2026-02-01") & (a.d <= "2026-04-30")
    for sl, col in (("mobile / Chrome", GREY), ("mobile / Safari iOS", BLUE)):
        d = a[win & (a.slice == sl) & (a.kpi == "payment step")]
        ax.plot(d.d, d.rate, color=col, lw=1.8, label=sl)
        if sl.endswith("iOS"):
            ax.plot(d.d, d.expected, color=col, ls="--", lw=1, label="expected (Safari iOS)")
            f = d[d.flagged]
            ax.scatter(f.d, f.rate, color=RED, s=10, zorder=3, label="flagged")
    ax.axvline(pd.Timestamp("2026-03-10"), color=RED, lw=0.8)
    ax.text(pd.Timestamp("2026-03-11"), 0.86, "release 10 Mar:\npayment widget", fontsize=8, color=RED)
    ax.yaxis.set_major_formatter(PCT)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_title("Payment-step pass rate, 7 days (SIMULATED)")
    ax.legend(fontsize=7.5, loc="lower left")
    return save(fig, "safari")


def slow_pdp():
    a = csv("anomaly_series")
    a["d"] = pd.to_datetime(a.d)
    sp = pd.read_parquet(SIM / "page_speed_daily.parquet")
    win = (a.d >= "2026-04-01") & (a.d <= "2026-07-31")
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    for sl, col in (("desktop / Mattress", GREY), ("mobile / Mattress", BLUE)):
        d = a[win & (a.slice == sl) & (a.kpi == "add-to-cart rate")]
        ax.plot(d.d, d.rate / d.rate[d.d < "2026-05-12"].median(), color=col, lw=1.8, label=f"{sl} add-to-cart (index)")
    s = sp[(sp.page_type == "Product page - mattress") & (sp.date >= "2026-04-01") & (sp.date <= "2026-07-31")]
    ax2 = ax.twinx()
    ax2.plot(s.date, s.lcp_mobile_p50_s, color=RED, lw=0.8, alpha=0.7, label="mobile LCP (s)")
    ax2.set_ylabel("mobile LCP, s", color=RED)
    ax2.tick_params(colors=RED)
    ax2.spines["right"].set_visible(True)
    ax2.grid(False)
    ax.axvline(pd.Timestamp("2026-05-12"), color=RED, lw=0.8, ls="--")
    ax.set_title("Mattress pages: carousel release 12 May (SIMULATED)")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, [lab.replace(" / Mattress add-to-cart (index)", " add-to-cart") for lab in l1] + l2, fontsize=7.5,
              loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    ax.set_ylabel("add-to-cart (index, before = 1)")
    return save(fig, "slow_pdp")


def shipping_by_category():
    f = csv("funnel_segments")
    c = f[f.dimension == "Category"].sort_values("shipping_step_abandonment")
    fig, ax = plt.subplots(figsize=(4.4, 3.2))
    cols = [RED if s in ("Bed base & bed", "Sofa") else BLUE for s in c.segment]
    ax.barh(c.segment, c.shipping_step_abandonment, color=cols)
    for y, v in enumerate(c.shipping_step_abandonment):
        ax.text(v + 0.005, y, f"{v:.0%}", va="center", fontsize=8.5, color=MUTED)
    ax.xaxis.set_major_formatter(PCT)
    ax.set_title("Delivery-step abandonment (SIMULATED)\nbulky items in red")
    ax.grid(axis="y", visible=False)
    return save(fig, "shipping")


# ------------------------------------------------------------------ page 6: testing
def tests_forest():
    t = csv("experiment_readout")
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    for i, r in enumerate(t.itertuples()):
        y = len(t) - 1 - i
        col_p = GREY if r.srm else BLUE
        ax.errorbar(r.primary_lift, y + 0.12, xerr=[[r.primary_lift - r.primary_ci_low], [r.primary_ci_high - r.primary_lift]],
                    fmt="o", color=col_p, ms=5, capsize=2, lw=1.4, label="primary KPI" if i == 0 else None)
        ax.errorbar(r.rpv_net_lift, y - 0.12, xerr=[[r.rpv_net_lift - r.rpv_net_ci_low], [r.rpv_net_ci_high - r.rpv_net_lift]],
                    fmt="D", color=GREY if r.srm else GREEN, ms=4.5, capsize=2, lw=1.4,
                    label="net revenue per visitor" if i == 0 else None)
        ax.text(0.42, y, r.decision.upper() if not r.srm else "INVALID (SRM)", va="center", fontsize=8.5,
                color=RED if r.srm else INK, fontweight="semibold")
    short = {"A": "A  Sticky add-to-cart (mobile)", "B": "B  '100 nights' near button",
             "C": "C  Bulky delivery fee on page", "D": "D  Mattress comparator"}
    ax.set_yticks(range(len(t)), [short[r.test_id] for r in t.itertuples()][::-1], fontsize=9)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlim(-0.15, 0.55)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))
    ax.set_title("Lift vs control with 95% intervals (SIMULATED)")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.45, -0.1), ncol=2)
    ax.grid(axis="y", visible=False)
    return save(fig, "tests")


def peeking():
    p = csv("peeking")
    fig, ax = plt.subplots(figsize=(4.4, 3.2))
    ax.plot(p.day, p.false_positive_if_stopped_at_first_win, color=RED, lw=1.8, label="stop at first p < 0.05")
    ax.axhline(p.false_positive_fixed_horizon.iloc[0], color=GREEN, ls="--", lw=1.2, label="read once at day 28")
    ax.axhline(0.05, color=GREY, lw=0.6)
    ax.yaxis.set_major_formatter(PCT)
    ax.set_xlabel("days the A/A test has run")
    ax.set_title("False 'winners' in an A/A test (2,000 runs)")
    ax.legend(fontsize=8)
    return save(fig, "peeking")


def power_curve():
    import stats_tests as st
    fig, ax = plt.subplots(figsize=(4.4, 3.2))
    mde = np.linspace(0.04, 0.25, 60)
    for base, col, lab in ((0.016, BLUE, "conversion 1.6%"), (0.09, GREY, "add-to-cart 9%")):
        n = [2 * st.sample_size_per_arm(base, m) / 6000 for m in mde]
        ax.plot(mde, n, color=col, lw=1.8, label=lab)
    ax.axhline(56, color=RED, ls="--", lw=0.8)
    ax.text(0.2, 60, "8 weeks", color=RED, fontsize=8)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("minimum detectable effect (relative)")
    ax.set_ylabel("days at 6,000 visitors/day")
    ax.set_title("How long a test must run (alpha 5%, power 80%)")
    ax.legend(fontsize=8)
    return save(fig, "power")


def build_all() -> dict:
    return {f.__name__: f() for f in (market, catalogue, prices, lighthouse, lighthouse_weight, ga4_funnel, ga4_segments,
                                      weekly_topline, mix_bars, reconciliation, safari, slow_pdp, shipping_by_category,
                                      tests_forest, peeking, power_curve)}


if __name__ == "__main__":
    print(build_all())
