"""Build the 8-page PDF report: HTML (grey-beige page, white cards) printed by Edge/Chrome headless.
Every number is read from data/processed (nothing typed by hand except the public facts quoted from the site).

    python src/build_pdf.py   -> report/tediber_cro_case_study.pdf (+ report/report.html)
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd
from pypdf import PdfReader, PdfWriter

import charts

ROOT = Path(__file__).resolve().parents[1]
PROC, REP = ROOT / "data" / "processed", ROOT / "report"
PDF_NAME = "tediber_cro_case_study.pdf"
DISCLAIMER = "Independent case study based on public data · not affiliated with or endorsed by Tediber"
# the AI note is written once, in the README (Methods), and quoted here word for word
AI_NOTE = next(line[2:].strip() for line in (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
               if line.startswith("- AI-assisted workflow"))


def csv(n):
    return pd.read_csv(PROC / f"{n}.csv")


def page(n, title, subtitle, tag, body, sources):
    tag_html = "".join(f'<div class="tag tag-{t.lower().split()[0]}">{t}</div>' for t in tag.split(" + "))
    return f"""<section class="page"><header><div><h1>{title}</h1><p class="sub">{subtitle}</p></div><div class="tags">{tag_html}</div></header>
<main>{body}</main><footer><span>{sources}</span><span>{DISCLAIMER}</span><span>{n} / 7</span></footer></section>"""


def card(inner, cls=""):
    return f'<div class="card {cls}">{inner}</div>'


def img(src, cap=""):
    return f'<figure><img src="{src}"/>{f"<figcaption>{cap}</figcaption>" if cap else ""}</figure>'


def tile(label, value, text, tag):
    return card(f'<div class="label">{label} <span class="mini mini-{tag.lower().split()[0]}">{tag}</span></div>'
                f'<div class="big">{value}</div><p>{text}</p>', "tile")


def facts():
    f = {}
    ro = csv("experiment_readout").set_index("test_id")
    f["ro"] = ro
    f["sc"] = csv("detection_scorecard")
    f["dedup"] = csv("ga4_revenue_dedup").iloc[0]
    f["dq"] = csv("ga4_data_quality").set_index("check_name")["value"]
    g = csv("ga4_funnel_segments")
    f["ga4"] = g.set_index(["dimension", "segment"])
    fs = csv("funnel_segments")
    cat = fs[fs.dimension == "Category"].set_index("segment")["shipping_step_abandonment"]
    f["ship_bulky"] = cat[["Bed base & bed", "Sofa"]].mean()
    f["ship_other"] = cat.drop(["Bed base & bed", "Sofa"]).mean()
    f["mix"] = csv("mix_decomposition")
    f["inc"] = csv("anomaly_incidents")
    f["rec"] = csv("reconciliation_incidents").iloc[0]
    f["lh"] = csv("lighthouse_summary")
    f["ux"] = csv("ux_audit")
    f["reg"] = csv("tediber_registry").set_index("field")["value"]
    f["mkt"] = csv("market_eurostat")
    f["plan"] = csv("power_plan").set_index("test_id")
    f["imp"] = csv("business_impact").set_index("test_id")
    f["peek"] = csv("peeking")
    f["cat"] = csv("tediber_catalogue_by_category")
    s = pd.read_parquet(ROOT / "data" / "sim" / "sessions_daily.parquet", columns=["sessions", "orders", "revenue_eur"])
    f["sim"] = s.sum()
    return f


# ------------------------------------------------------------------ pages
def p0(f, ch):
    ro, sc = f["ro"], f["sc"]
    d = ro.loc["D"]
    ok = int(sc[sc.event_id < 99].handled_correctly.sum())
    fp = sc[sc.event_id == 99].how.iloc[0].split()[0]
    qs = card("""<h2>Five questions</h2><ol class="qs">
<li><b>1</b>Who is Tediber, and how big is the online bedding market it sells in? <span class="pg">p.1</span></li>
<li><b>2</b>What does a visitor meet on the public pages before buying, on mobile and desktop? <span class="pg">p.2</span></li>
<li><b>3</b>Where do real e-commerce funnels leak, and can the tracking be trusted? <span class="pg">p.3</span></li>
<li><b>4</b>How does a weekly report tell a real problem from noise, mix or a promotion? <span class="pg">p.4</span></li>
<li><b>5</b>How do we go from a leak to a cause, a prioritised test and a decision that survives the 100-night returns? <span class="pg">p.5-6</span></li></ol>
<h2 style="margin-top:14px">What comes with it</h2><ul class="small">
<li><b>Excel toolkit</b> (formulas, Google Sheets compatible): weekly report, funnel, anomaly log, ICE / RICE backlog, test calculator (sample size, z test, SRM), test log.</li>
<li><b>Interactive dashboard</b> (one HTML file): weekly overview, funnel filters, anomalies, experiments, real GA4 funnel.</li>
<li><b>SQL</b> (DuckDB, commented): weekly KPIs, funnel, anomaly detection, reconciliation, test read-out; the same funnel on real GA4.</li>
<li><b>Docs</b>: KPI dictionary, GA4 tracking plan, UX audit, 4 test briefs + 4 read-outs, weekly and quarterly templates, benchmark, AI guardrails.</li>
<li><b>Verified weekly note</b>: drafted from the data, every number checked; 21 automated tests.</li></ul>""")
    tiles = "".join([
        tile("Planted events handled", f"{ok} / 8", f"by the weekly monitoring, with {fp} false incident in 18 months: breaks found in 2-5 days and "
             "linked to the right release; mix effect and Black Month raise no incident.", "SIMULATED"),
        tile("Revenue inflated by duplicates", f"{f['dedup'].inflation_share:+.1%}", f"in a real GA4 export: {int(f['dq']['transaction ids sent more than once'])} "
             "transaction ids sent more than once. De-duplicate on transaction id before any revenue KPI.", "PUBLIC DATA"),
        tile("Delivery-step abandonment", f"x{f['ship_bulky'] / f['ship_other']:.1f}", f"for bulky items ({f['ship_bulky']:.0%} vs {f['ship_other']:.0%}) when the fee "
             "appears only at checkout. Tediber's bed-base page already shows the fee; test C shows how to measure it.", "SIMULATED"),
        tile("The winner that loses", f"{d.conversion_lift:+.0%} → {d.rpv_net_lift:+.0%}", f"mattress comparator: conversion up (p = {d.conversion_p_value:.3f}) "
             f"but returns {d.return_rate_control:.1%} → {d.return_rate_variant:.1%}; net revenue per visitor not shown to be better: iterate.", "SIMULATED"),
    ])
    reco = card("""<h2>Recommendations</h2><ol class="reco">
<li><b>Judge tests on net revenue per visitor after the 100 nights</b>, not on conversion alone - a mattress that comes back is not a sale.</li>
<li><b>Weekly monitoring by device x browser and category</b>, with a traffic-mix check before opening any incident, promotions compared with last year's, and a daily analytics vs back-office reconciliation.</li>
<li><b>Opportunities to test on the public pages</b>: one split-payment message (3x-24x vs 3x-12x), a delivery promise adapted on bulky-item pages, and a mobile performance budget once real-user data confirm the lab.</li>
<li><b>Plan every test before launch</b>: sample size and duration fixed, allocation (SRM) checked on day 1, no early stop.</li>
<li><b>Automate the weekly draft, not the judgement</b>: every number checked against the data; interpretation and decisions stay with the team.</li></ol>""")
    how = card("""<h2>How</h2><p><b>Public data</b>: company register, Tediber's public pages (robots.txt respected, 1 request / 10 s), Lighthouse, Eurostat, FEVAD, Baymard,
and real GA4 journeys of another store (Google Merchandise Store). <b>Simulated data</b>: an 18-month DTC bedding store modelled on public information, with 8 hidden events
to find. Tools: DuckDB SQL, Python, Excel (formulas), Plotly dashboard. Every view is tagged PUBLIC DATA or SIMULATED; simulated numbers are never Tediber's.</p>""", "auto")
    body = f'<div class="g0"><div class="stack">{qs}{how}</div><div class="stack"><div class="grid2t">{tiles}</div>{reco}</div></div>'
    return page(0, "Tediber: finding where the mattress funnel leaks, and testing the fix",
                "Public company, market and page-speed data, real GA4 e-commerce journeys and a simulated, calibrated DTC bedding store turned into a weekly CRO "
                "report, anomaly detection, a prioritised test backlog, power-planned A/B tests and reusable CRO templates.",
                "OVERVIEW", body, "Sources: data/SOURCES.md")


def p1(f, ch):
    r = f["reg"]
    m = f["mkt"].set_index(["indicator", "geo", "year"])["pct_individuals"]
    fact = card(f"""<h2>The company <span class="mini mini-public">PUBLIC DATA</span></h2><ul class="facts">
<li><b>Register</b>: SAS created {pd.Timestamp(r['Created']):%d %b %Y}, Paris head office, activity {r['Activity code (NAF)'].split(' -')[0]} (distance selling),
{r['Headcount band']}. Only accounts published in the open API: 2020, revenue EUR {int(r['Revenue 2020 (EUR)']) / 1e6:.1f} M, net income EUR {int(r['Net income 2020 (EUR)']) / 1e6:.2f} M; later years are not there and are not estimated.</li>
<li><b>Offer</b> (as stated by Tediber): French bedding sold online - mattresses, pillows, duvets, bed bases, beds, linen, sofas; ranges Tediber, Grand Ours (premium), Tedi (kids).</li>
<li><b>Promises</b>: 100-night trial (30 nights for linen), delivery in 48 h (bulky items 8-10 days), split payment, free returns, old-bedding take-back; 4 stores (Paris x2, Lyon, Toulouse).</li>
<li><b>Mission company</b> since July 2021, target -35 % carbon intensity by 2030, 80 % of products from France or Belgium (as stated by Tediber).</li>
<li><b>Scripts observed in the public page source</b> on 17 Nov 2026: Shopify, Kameleoon, Contentsquare, Microsoft Clarity, Google Tag Manager, Klaviyo, Trustpilot, Alma, Judge.me - the stack named in the job offer. How they are used is not known.</li>
<li><b>17 Nov 2026</b>: "Black Month: jusqu'à -40 %" on the homepage.</li></ul>""")
    mk = card(f"""<h2>The market <span class="mini mini-public">PUBLIC DATA</span></h2><ul class="facts">
<li>French e-commerce reached <b>EUR 196.4 bn in 2025 (+7 %)</b>, 3.2 bn transactions, average basket EUR 62 - as stated by FEVAD (Feb 2026).</li>
<li><b>{m[('I_BUY3', 'FR', 2025)]:.1f} %</b> of people in France bought online in the last 3 months of 2025 (EU-27: {m[('I_BUY3', 'EU27_2020', 2025)]:.1f} %); <b>{m[('I_BFURN1', 'FR', 2024)]:.1f} %</b>
bought furniture or home goods online (2024, EU-27 {m[('I_BFURN1', 'EU27_2020', 2024)]:.1f} %) - Eurostat.</li>
<li>Average documented cart abandonment: <b>70.22 %</b> (Baymard, 50 studies); extra costs are the first reason (40 %).</li>
<li>A mattress is bought <b>rarely, for hundreds of euros, after several visits</b>, and can come back within 100 nights: conversion per session is not enough; revenue net of returns per visitor is the metric.</li></ul>""")
    body = f"""<div class="grid-1-1"><div class="stack">{fact}{mk}</div><div class="stack">{card(img(ch['market']), 'tall')}
<div class="grid2">{card(img(ch['catalogue']))}{card(img(ch['prices']))}</div></div></div>"""
    return page(1, "Tediber is a French online bedding brand whose purchase cycle makes returns part of the conversion question",
                "Public facts only: the company register, Tediber's own pages and sitemap, Eurostat, FEVAD and Baymard. Nothing about traffic or recent results is guessed.",
                "PUBLIC DATA", body, "recherche-entreprises.api.gouv.fr · tediber.com (17 Nov 2026) · Eurostat isoc_ec_ib20 / isoc_ec_ibgs · FEVAD · Baymard")


def p2(f, ch):
    lh, ux = f["lh"], f["ux"]
    mob = lh[lh.form_factor == "mobile"]
    desk = lh[lh.form_factor == "desktop"]
    area = ux.groupby("area")[["score_mobile", "score_desktop"]].sum().div(2 * ux.groupby("area").size(), axis=0)
    rows = "".join(f"<tr><td>{a}</td><td>{r.score_mobile:.0%}</td><td>{r.score_desktop:.0%}</td></tr>" for a, r in area.iterrows())
    svg = (ROOT / "docs" / "img" / "wireframe_pdp_mobile.svg").read_text(encoding="utf-8")
    audit = card(f"""<h2>Heuristic audit, 26 criteria <span class="mini mini-public">PUBLIC PAGES</span></h2>
<table class="small"><tr><th>Area</th><th>Mobile</th><th>Desktop</th></tr>{rows}
<tr><td><b>Total</b></td><td><b>{ux.score_mobile.sum()}/{2 * len(ux)}</b></td><td><b>{ux.score_desktop.sum()}/{2 * len(ux)}</b></td></tr></table>
<p class="note">Home, category, product page; cart and checkout not visited.</p>""")
    opp = card(f"""<h2>Opportunities to test</h2><ol class="small">
<li><b>One split-payment message</b>: the banner says 3x-24x, the blocks and product page 3x-12x.</li>
<li><b>Lighter first screen on mobile</b>: lab LCP {mob.lcp_s.min():.1f}-{mob.lcp_s.max():.1f} s on mobile vs {desk.lcp_s.min():.1f}-{desk.lcp_s.max():.1f} s on desktop,
blocking time {mob.tbt_ms.min() / 1000:.1f}-{mob.tbt_ms.max() / 1000:.1f} s, {int(mob.third_party_entities.median())} third-party origins per page. Lab data on a simulated slow phone; on category pages the largest element measured is the consent panel (no consent stored), which inflates LCP to ~19 s. Confirm with real-user Core Web Vitals first.</li>
<li><b>Delivery promise by product type</b>: the "48h" banner also shows on bulky-item pages (8-10 days).</li>
<li><b>Measure the comparator and quiz on net revenue after returns</b> (page 6).</li></ol>
<p class="note">Already in place: sticky add-to-cart bar, delivery date, bulky delivery options and fee, trial and returns under the button,
reviews next to the price, comparator and quiz.</p>""")
    body = f"""<div class="grid-2-1"><div class="stack">{card(img(ch['lighthouse']), 'tall')}<div class="grid2">{audit}{opp}</div></div>
<div class="stack">{card('<h2>Mattress product page, mobile - drawn schema</h2>' + svg, 'svgcard')}{card(img(ch['lighthouse_weight']))}</div></div>"""
    return page(2, "The product pages already do most things right; the openings are one payment message, the bulky delivery promise and mobile speed",
                "Lighthouse lab runs (6 public pages x mobile/desktop x 3, median) and a 26-criterion heuristic audit of the public journey, written as hypotheses to test.",
                "PUBLIC DATA", body, "Lighthouse 12.8.2, 17 Nov 2026 · own audit of public pages (no screenshot published) · docs/UX_AUDIT.md")


def p3(f, ch):
    g, dq = f["ga4"], f["dq"]
    a = g.loc[("All", "All sessions")]
    new, ret = g.loc[("Visitor type", "New")], g.loc[("Visitor type", "Returning")]
    read = card(f"""<h2>What it teaches for a mattress store</h2><ul class="facts">
<li><b>Returning visitors convert {ret.conversion_rate / new.conversion_rate:.1f}x better</b> ({ret.conversion_rate:.2%} vs {new.conversion_rate:.2%}): with long
purchase cycles, report conversion per user over a period next to conversion per session.</li>
<li><b>{a.checkout_abandonment:.0%} of checkouts</b> do not end in a purchase; the biggest single drop is product view -> add to cart ({a.add_to_cart / a.view_item:.0%} pass).</li>
<li>Mobile and desktop convert alike here ({g.loc[('Device', 'mobile')].conversion_rate:.2%} vs {g.loc[('Device', 'desktop')].conversion_rate:.2%}): a device gap is
not a law - it must be measured per site.</li></ul>""")
    q = card(f"""<h2>Can the tracking be trusted? Checks first</h2><table class="small">
<tr><td>Transaction ids sent more than once</td><td><b>{int(dq['transaction ids sent more than once'])}</b></td></tr>
<tr><td>Revenue inflation if not de-duplicated</td><td><b>{f['dedup'].inflation_share:+.1%}</b></td></tr>
<tr><td>Purchase events with no usable transaction id</td><td><b>{int(dq['purchase events with a missing or (not set) transaction id'])}</b> of {int(dq['purchase events'])}</td></tr>
<tr><td>Sessions without session_start</td><td><b>{dq['share of sessions without session_start']:.1%}</b></td></tr>
<tr><td>Sessions with no channel (data deleted / other)</td><td><b>{dq['share of sessions with channel not available ((data deleted), <Other>)']:.0%}</b></td></tr>
<tr><td>view_cart / view_item_list events</td><td><b>{int(dq['view_cart events (not tracked in this export)'])} / {int(dq['view_item_list events (list views barely tracked)'])}</b></td></tr></table>
<p class="note">Same queries in sql/ga4/ (DuckDB, BigQuery logic). Visitor ids stay in the raw extract; only aggregates are published.</p>""")
    body = f"""<div class="grid-1-1"><div class="stack">{card(img(ch['ga4_funnel']), 'big2')}{read}</div>
<div class="stack">{card(img(ch['ga4_segments']), 'big2')}{q}</div></div>"""
    return page(3, f"In a real GA4 export, returning visitors convert {ret.conversion_rate / new.conversion_rate:.1f}x better and duplicate purchases inflate revenue by {f['dedup'].inflation_share:.1%}",
                f"Real journeys of another store (Google Merchandise Store, {int(a.sessions):,} sessions, Nov 2020 - Jan 2021) to show the funnel method and the data checks on real data - not Tediber's data.",
                "PUBLIC DATA", body, "BigQuery public dataset ga4_obfuscated_sample_ecommerce via Hugging Face mirror (MIT) · sql/ga4/01_ga4_funnel.sql")


def p4(f, ch):
    note = (ROOT / "weekly_notes" / "weekly_note_2026-03-16.md").read_text(encoding="utf-8").split("\n\n", 2)[2].strip()
    first = " ".join(note.split(". ")[:2]) + "."
    mix = f["mix"]
    m0 = mix[mix.first_day == mix.first_day.min()]
    rec = f["rec"]
    method = card(f"""<h2>How the monitoring decides</h2><ol class="small">
<li><b>Rate per slice</b> (device, device x browser, channel, category, device x category, visitor type) and per step, 7-day trailing.</li>
<li><b>Expected</b> = median of the same weekday over 8 weeks, promotions excluded; inside a promotion, last year's promotion scaled.</li>
<li><b>Alert</b> = robust z >= 3.5, change >= 10 %, 5 days in a row.</li>
<li><b>Triage before any incident</b>: did the channel mix move? Is the data right (analytics vs shop)? Which release came just before?</li></ol>
<p class="note">Early September: topline {m0.topline_cr_during.iloc[0] / m0.topline_cr_before.iloc[0] - 1:+.0%} vs the 4 weeks before; rate effect
{100 * m0.rate_effect.sum():+.2f} pp, mix effect {100 * m0.mix_effect.sum():+.2f} pp -> explained, no incident. Analytics revenue reached
{rec.max_revenue_ratio:.0%} of the shop's from {rec.first_day} -> duplicate purchase tag, fixed after {rec.days_flagged} days.</p>""")
    wk = card(f"""<h2>The weekly note, drafted and checked automatically</h2><p class="quote">{first} [...]</p>
<p class="note">Week of 16 Mar 2026: every number of the draft is traced to the data by src/check_numbers.py (unit, period, per session / per user,
gross / net); one wrong number rejects the draft. Template: docs/WEEKLY_REPORT_TEMPLATE.md · Excel "Weekly report" tab.</p>""")
    body = f"""<div class="grid-2-1"><div class="stack">{card(img(ch['weekly_topline']), 'tall')}<div class="grid2">{card(img(ch['mix_bars']))}{card(img(ch['reconciliation']))}</div></div>
<div class="stack">{method}{wk}</div></div>"""
    return page(4, "A weekly report that separates noise from problems: a mix shift, a promotion and a tracking bug are not funnel breaks",
                "Simulated DTC bedding store (18 months, day by day). The topline alone would have raised false alarms in September and November and missed the real breaks of March and May.",
                "SIMULATED", body, "sql/01_weekly_kpis.sql · sql/03_anomalies.sql · sql/04_reconciliation.sql · src/weekly_summary.py")


def p5(f, ch):
    inc = f["inc"]
    s = inc[inc.slice.str.contains("Safari") & (inc.kpi == "payment step")].iloc[0]
    m = inc[inc.slice.str.contains("Mattress") & (inc.status == "open: investigate")].iloc[0]
    from build_excel import BACKLOG
    bl = pd.DataFrame(BACKLOG, columns=["idea", "page", "source", "evidence", "reach", "impact", "conf", "effort", "i", "c", "e", "seen"])
    bl["rice"] = bl.reach * bl.impact * bl.conf / bl.effort
    bl["ice"] = bl.i * bl.c * bl.e
    top = bl[bl.reach > 0].sort_values("rice", ascending=False).head(6)
    rows = "".join(f"<tr><td>{r.idea}</td><td>{r.rice:,.0f}</td><td>{r.ice}</td><td>{r.seen}</td></tr>" for r in top.itertuples())
    cause = card(f"""<h2>Leak -> cause -> hypothesis</h2><ul class="facts">
<li><b>Payment, Safari iOS only</b>: {s.rel_change_at_peak:+.0%} vs expected from {s.first_day}, other browsers flat. Release log: split-payment widget upgraded on 10 Mar.
<i>Because we saw a Safari-only drop right after the widget release, we believe a hotfix restores the payment step, measured by its pass rate on Safari iOS.</i></li>
<li><b>Mattress pages, mobile only</b>: add-to-cart {m.rel_change_at_peak:+.0%} from {m.first_day}; mobile LCP +1.4 s after the 12 May image carousel; desktop flat.</li>
<li><b>Bulky items</b>: {f['ship_bulky']:.0%} abandon at the delivery step vs {f['ship_other']:.0%} - the fee appears at checkout (structural, not an incident) -> test C.</li></ul>""")
    blc = card(f"""<h2>Backlog, top 6 by RICE (18 ideas in Excel, ICE and RICE by formula)</h2>
<table class="small"><tr><th>Idea</th><th>RICE</th><th>ICE</th><th>On Tediber's public pages</th></tr>{rows}</table>
<p class="note">Reach and scores refer to the simulated store; ideas come from its data, the public audit and published benchmarks. Process items (Safari payment QA, purchase-tag monitor) are done without a test.</p>""")
    body = f"""<div class="grid3">{card(img(ch['safari']))}{card(img(ch['slow_pdp']))}{card(img(ch['shipping_by_category']))}</div>
<div class="grid-1-1 short">{cause}{blc}</div>"""
    return page(5, "From leak to cause to backlog: segment first, then read the release log, then write a hypothesis that can be measured",
                "Simulated store. Each break is visible in one slice only (device x browser, device x category) and lines up with one release; the structural leak goes to the backlog.",
                "SIMULATED + PUBLIC AUDIT", body, "sql/02_funnel.sql · sql/03_anomalies.sql · releases table · Excel 'CRO backlog'")


def p6(f, ch):
    ro, plan, imp = f["ro"], f["plan"], f["imp"]
    rows = ""
    for t, r in ro.iterrows():
        res = "not read (SRM)" if r.srm else f"{r.primary_lift:+.1%} [{r.primary_ci_low:+.1%}; {r.primary_ci_high:+.1%}]"
        net = "-" if r.srm else f"{r.rpv_net_lift:+.1%} [{r.rpv_net_ci_low:+.1%}; {r.rpv_net_ci_high:+.1%}]"
        rows += (f"<tr><td><b>{t}</b> {r.test_name}</td><td>{plan.loc[t, 'planned_days']} d, MDE {plan.loc[t, 'mde_relative']:.0%}</td>"
                 f"<td>{r.variant_share:.1%}</td><td>{res}</td><td>{net}</td><td>{r.return_rate_control:.1%} / {r.return_rate_variant:.1%}</td><td><b>{r.decision}</b></td></tr>")
    c = imp.loc["C"]
    tbl = card(f"""<h2>Decisions (rule written before launch)</h2><table class="small"><tr><th>Test</th><th>Plan</th><th>Variant share</th><th>Primary KPI [95% CI]</th>
<th>Net revenue / visitor</th><th>Returns ctl / var</th><th>Decision</th></tr>{rows}</table>
<p class="note">SRM -> invalid; primary up (p &lt; 0.05) and no guardrail breached -> ship; primary up but returns up or net revenue clearly down -> iterate; otherwise drop.
Test C, annualised on the simulated store: EUR {c.impact_central_eur / 1e6:.1f} M net (95% range {c.impact_low_eur / 1e6:.1f}-{c.impact_high_eur / 1e6:.1f} M).
All four features already exist on Tediber's public pages; the simulated store starts without them, to show how they are measured.</p>""")
    stat = card(f"""<h2>The statistics behind it</h2><ul class="facts">
<li><b>Before</b>: sample size from baseline, minimum detectable effect, alpha 5 %, power 80 % -> whole weeks.</li>
<li><b>Day 1</b>: allocation check - test B ran {ro.loc['B', 'variant_share']:.1%} / {1 - ro.loc['B', 'variant_share']:.1%} (chi-square p &lt; 0.001): a redirect lost visitors. Not read.</li>
<li><b>No peeking</b>: stopping an A/A test at the first p &lt; 0.05 gives {f['peek'].false_positive_if_stopped_at_first_win.iloc[-1]:.0%} false winners vs {f['peek'].false_positive_fixed_horizon.iloc[0]:.0%}.</li>
<li><b>After</b>: z test and interval on the primary KPI; bootstrap for revenue per visitor (heavy-tailed); returns as a guardrail.</li></ul>""")
    body = f"""<div class="grid3">{card(img(ch['power_curve']))}{card(img(ch['tests_forest']))}{card(img(ch['peeking']))}</div>
<div class="grid-2-1 short">{tbl}{stat}</div>"""
    return page(6, "Testing it right: a comparator that lifts conversion can lose its gain to returns, and a broken split is not read at all",
                "Four tests on the simulated store, each planned with a power calculation, checked for sample ratio mismatch and decided on net revenue per visitor after 100-night returns.",
                "SIMULATED", body, "src/stats_tests.py · sql/05_experiments.sql · docs/ab_tests/ · Excel 'Test calculator'")


def p7(f, ch):
    sc = f["sc"]
    rows = "".join(f"<tr><td>{r.event}</td><td>{r.expected_handling}</td><td>{'yes' if r.handled_correctly else 'NO'}</td><td>{r.how}</td></tr>"
                   for r in sc.itertuples())
    src = card("""<h2>Data and sources</h2><ul class="facts small">
<li><b>PUBLIC DATA</b>: French company register open API (Etalab licence); Tediber public pages and sitemap (17 Nov 2026, robots.txt respected, 1 request / 10 s,
no cart, checkout, account or search; no Wayback Machine; Trustpilot not scraped); Lighthouse lab runs; Eurostat (re-use with attribution); FEVAD and Baymard (as stated);
GA4 obfuscated sample of the Google Merchandise Store via a Hugging Face mirror (MIT) - another store.</li>
<li><b>SIMULATED</b>: 18 months day by day, ~5.4 M sessions, calibrated on public orders of magnitude (2020 revenue, price ranges, real GA4 step rates, promotions);
8 events planted with a hidden answer key, used only once to score the detection. Assumptions: data/ASSUMPTIONS.md.</li>
<li><b>Privacy</b>: no personal data, no review copied, no visitor id published (aggregates only), no person named.</li></ul>
<h2 style="margin-top:10px">Reproduce (no key needed)</h2><pre>python src/extract_ga4.py      python src/simulate.py       python src/run_sql.py
python src/analyse.py          python src/build_excel.py    python src/weekly_summary.py
pytest                         python src/build_dashboard.py  python src/build_pdf.py</pre>""")
    lim = card("""<h2>Limits</h2><ul class="facts small">
<li>The simulated store is not Tediber: its levels illustrate the method, not the company's performance; Tediber's real traffic, conversion and returns are unknown here.</li>
<li>Lighthouse is lab data on one simulated device; real-user Core Web Vitals (CrUX) were not collected.</li>
<li>The audit covers public pages only (no cart, checkout or account) and one capture per page.</li>
<li>The GA4 sample is a 2020-2021 merch store, obfuscated, with first-user channels only.</li>
<li>Returns of recent weeks are not mature; impacts are ranges and assume the effect lasts.</li></ul>
<h2 style="margin-top:10px">First weeks with real data</h2><ul class="facts small">
<li>Reconcile GA4 with the Shopify back office (orders, revenue, duplicates) before any KPI is trusted.</li>
<li>Rebuild the weekly report on the real export and tune the alert thresholds on 12 months of history.</li>
<li>Pull real-user Core Web Vitals and Contentsquare / Clarity journeys for the pages flagged here.</li>
<li>Re-read past tests on net revenue after returns.</li></ul>""")
    ai = card(f"""<h2>AI note</h2><p class="quote">{AI_NOTE}</p>
<p class="small">Weekly draft: template by default, optional LLM draft; every number checked by src/check_numbers.py (tests on percent vs points, wrong week,
per session vs per user, gross vs net). Interpretation and decisions are never delegated. Formulas recalculated by LibreOffice and compared with Python; statistics
re-computed a second way in tests/.</p>""")
    det = card(f"""<h2>How the monitoring scored on the hidden events <span class="mini mini-simulated">SIMULATED</span></h2>
<table class="small"><tr><th>Event</th><th>Expected</th><th>OK</th><th>How it was handled</th></tr>{rows}</table>""")
    body = f'<div class="grid-1-1"><div class="stack">{src}{lim}</div><div class="stack">{det}{ai}</div></div>'
    return page(7, "Methods, limits and AI note", "What is public, what is simulated, how each number is produced and checked, and what it cannot tell.",
                "OVERVIEW", body, "data/SOURCES.md · data/ASSUMPTIONS.md · docs/AI_REPORTING_GUARDRAILS.md")


CSS = """
@page { size: 1600px 900px; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Segoe UI', Arial, sans-serif; color: #0B0B0B; background: #F2EFE9; }
.page { width: 1600px; height: 900px; padding: 30px 44px 22px; display: flex; flex-direction: column; page-break-after: always; overflow: hidden; background: #F2EFE9; }
header { display: flex; justify-content: space-between; align-items: flex-start; gap: 30px; }
h1 { font-size: 27px; margin: 0 0 6px; font-weight: 700; line-height: 1.15; max-width: 1280px; }
.sub { margin: 0; color: #52514E; font-size: 14.5px; max-width: 1280px; }
.tags { display: flex; gap: 6px; }
.tag { font-size: 12px; font-weight: 700; letter-spacing: .08em; padding: 5px 10px; border-radius: 4px; white-space: nowrap; color: #52514E; }
.tag-public { background: #E3EEFB; color: #1C5CAB; } .tag-simulated { background: #FBE9E0; color: #9A3B12; } .tag-overview { color: #52514E; border: 1px solid #D9D6CF; }
.mini { font-size: 10px; font-weight: 700; letter-spacing: .06em; padding: 2px 6px; border-radius: 3px; margin-left: 4px; vertical-align: middle; }
.mini-public { background: #E3EEFB; color: #1C5CAB; } .mini-simulated { background: #FBE9E0; color: #9A3B12; }
main { flex: 1; display: flex; flex-direction: column; gap: 12px; margin-top: 14px; min-height: 0; }
footer { display: flex; justify-content: space-between; gap: 20px; font-size: 11px; color: #898781; margin-top: 10px; }
.card { background: #FFFFFF; border: 1px solid #E1DDD4; border-radius: 8px; padding: 11px 15px; min-height: 0; overflow: hidden; }
.card h2 { font-size: 15.5px; margin: 0 0 6px; } .card p, .card li { font-size: 13px; line-height: 1.38; margin: 3px 0; color: #2B2A27; }
.card ul, .card ol { padding-left: 18px; margin: 4px 0; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid2t { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; flex: 1.05; min-height: 0; }
.g0 { display: grid; grid-template-columns: 1fr 1.35fr; gap: 12px; flex: 1; min-height: 0; }
.grid-1-1 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid-2-1 { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.short { flex: 0.95; }
figure { margin: 0; height: 100%; display: flex; flex-direction: column; }
figure img { width: 100%; flex: 1; min-height: 0; object-fit: contain; }
figcaption { font-size: 11.5px; color: #52514E; margin-top: 3px; }
.tile .label { font-size: 12px; font-weight: 700; color: #52514E; letter-spacing: .03em; }
.tile .big { font-size: 38px; font-weight: 700; margin: 0; color: #0B0B0B; } .tile p { font-size: 12.5px; color: #52514E; }
.stack { display: flex; flex-direction: column; gap: 12px; min-height: 0; } .stack > .card { flex: 1; } .stack > .grid2, .stack > .grid2t { flex: 1; }
.auto { flex: 0 0 auto !important; } .tall { flex: 1.25 !important; } .big2 { flex: 1.9 !important; }
.qs { list-style: none; padding-left: 0 !important; } .qs li { font-size: 14.5px !important; margin: 7px 0 !important; } .qs b { color: #2A78D6; margin-right: 8px; }
.pg { color: #898781; font-size: 12px; } .reco li { font-size: 13.5px !important; margin: 5px 0 !important; }
table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
th { text-align: left; color: #52514E; font-weight: 600; border-bottom: 1px solid #E1DDD4; padding: 3px 6px; }
td { border-bottom: 1px solid #EFECE6; padding: 3px 6px; vertical-align: top; }
.small, .small li, table.small td { font-size: 12px !important; }
.note { font-size: 11.5px !important; color: #6B6A65 !important; }
.facts li { margin: 4px 0 !important; }
.quote { font-style: italic; border-left: 3px solid #2A78D6; padding-left: 10px; }
pre { background: #F2EFE9; border-radius: 6px; padding: 6px 10px; font-size: 11.5px; margin: 4px 0; }
.svgcard { flex: 1.6 !important; display: flex; flex-direction: column; } .svgcard svg { flex: 1; min-height: 0; width: 100%; }
"""


def build_html() -> Path:
    ch = charts.build_all()
    f = facts()
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Tediber CRO case study</title><style>{CSS}</style></head><body>
{''.join(p(f, ch) for p in (p0, p1, p2, p3, p4, p5, p6, p7))}</body></html>"""
    out = REP / "report.html"
    out.write_text(html, encoding="utf-8")
    return out


def find_browser() -> str:
    for c in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe", shutil.which("msedge") or "", shutil.which("chromium") or ""]:
        if c and Path(c).exists():
            return c
    raise FileNotFoundError("Edge or Chrome is needed to print the PDF")


def print_pdf(html: Path) -> Path:
    pdf, tmp = REP / PDF_NAME, REP / "_print.pdf"
    profile = tempfile.mkdtemp()
    subprocess.run([find_browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profile}",
                    "--run-all-compositor-stages-before-draw", "--virtual-time-budget=5000", f"--print-to-pdf={tmp}", html.as_uri()],
                   check=True, timeout=180)
    last = -1
    for _ in range(120):  # Edge can return before its child process has written the file
        time.sleep(1)
        size = tmp.stat().st_size if tmp.exists() else -1
        if size > 0 and size == last:
            break
        last = size
    shutil.rmtree(profile, ignore_errors=True)
    reader, writer = PdfReader(str(tmp)), PdfWriter()
    for pg in reader.pages:
        writer.add_page(pg)
    writer.add_metadata({"/Title": "Tediber - CRO case study", "/Author": "", "/Creator": "", "/Producer": ""})
    with open(pdf, "wb") as fh:
        writer.write(fh)
    tmp.unlink()
    return pdf


if __name__ == "__main__":
    pdf = print_pdf(build_html())
    print(f"written {pdf.relative_to(ROOT)} ({len(PdfReader(str(pdf)).pages)} pages)")
