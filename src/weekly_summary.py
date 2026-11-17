"""Weekly CRO note (SIMULATED store): fact sheet -> draft -> number check -> publish or reject.

1. build a fact sheet for the week from data/processed (weekly KPIs, incidents, mix monitor, reconciliation);
2. draft 5-8 sentences: by default with a sentence template (no key needed); optionally with an LLM
   (src/llm_client.py, only if .env holds LLM_PROVIDER and LLM_API_KEY);
3. check every number with src/check_numbers.py; a draft with one wrong number is rejected, never published.
The analyst still reads the note and owns the interpretation and the decision (docs/AI_REPORTING_GUARDRAILS.md).

    python src/weekly_summary.py                    (week of 16 Mar 2026, the week shown in the report)
    python src/weekly_summary.py --week 2026-09-07  (any Monday of the data)
Output: weekly_notes/weekly_note_<week>.md and weekly_notes/weekly_note_<week>.facts.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import check_numbers
import llm_client

ROOT = Path(__file__).resolve().parents[1]
PROC, OUT = ROOT / "data" / "processed", ROOT / "weekly_notes"
DEFAULT_WEEK = "2026-03-16"


def _f(metric, value, unit, period="current", segment="All", basis=None, label=""):
    return {"metric": metric, "segment": segment, "value": round(float(value), 6), "unit": unit, "period": period,
            "basis": basis, "label": label or f"{metric} ({segment}, {period})"}


def build_facts(week: str) -> dict:
    k = pd.read_csv(PROC / "weekly_kpis.csv", parse_dates=["week_start"])
    w = pd.Timestamp(week)
    cur = k[(k["week_start"] == w)]
    if cur.empty:
        raise SystemExit(f"no complete week starting {week} in weekly_kpis.csv")
    prev = k[k["week_start"] == w - pd.Timedelta(days=7)].set_index(["dimension", "segment"])
    ly = k[k["week_start"] == w - pd.Timedelta(days=364)].set_index(["dimension", "segment"])
    a = cur[cur["dimension"] == "All"].iloc[0]
    pa = prev.loc[("All", "All")]
    facts = [
        _f("sessions", a["sessions"], "count", label="sessions"),
        _f("sessions", 100 * a["sessions_wow"], "pct", "wow", label="sessions, week on week"),
        _f("conversion", 100 * a["conversion_rate"], "pct", basis="per_session", label="conversion per session"),
        _f("conversion", 100 * a["conversion_per_user"], "pct", basis="per_user", label="conversion per user"),
        _f("conversion", 100 * pa["conversion_rate"], "pct", "previous", basis="per_session", label="conversion last week"),
        _f("conversion", 100 * (a["conversion_rate"] - pa["conversion_rate"]), "pp", "wow", basis="per_session",
           label="conversion, week on week (points)"),
        _f("conversion", 100 * a["conversion_rate_wow"], "pct", "wow", basis="per_session", label="conversion, week on week (relative)"),
        _f("aov", a["aov_eur"], "eur", label="average order value"),
        _f("aov", 100 * a["aov_wow"], "pct", "wow", label="average order value, week on week"),
        _f("rpv", a["revenue_per_visit_eur"], "eur", basis="gross", label="revenue per visit (gross)"),
        _f("rpv", a["net_revenue_per_visit_eur"], "eur", basis="net", label="revenue per visit (net of returns)"),
        _f("rpv", 100 * a["rpv_wow"], "pct", "wow", basis="gross", label="revenue per visit, week on week"),
        _f("atc", 100 * a["add_to_cart_rate"], "pct", label="add-to-cart rate"),
        _f("checkout_abandonment", 100 * a["checkout_abandonment"], "pct", label="checkout abandonment"),
        _f("checkout_abandonment", 100 * a["checkout_abandonment_wow_pts"], "pp", "wow", label="checkout abandonment, week on week"),
        _f("revenue", a["revenue_eur"], "eur", basis="gross", label="revenue (gross)"),
        _f("revenue", a["revenue_eur"] - a["returned_revenue_eur"], "eur", basis="net", label="revenue net of returns"),
    ]
    if ("All", "All") in ly.index:
        la = ly.loc[("All", "All")]
        facts += [_f("sessions", 100 * a["sessions_yoy"], "pct", "yoy", label="sessions vs same week last year"),
                  _f("conversion", 100 * (a["conversion_rate"] - la["conversion_rate"]), "pp", "yoy", basis="per_session",
                     label="conversion vs same week last year (points)"),
                  _f("conversion", 100 * a["conversion_rate_yoy"], "pct", "yoy", basis="per_session",
                     label="conversion vs same week last year (relative)")]
    for dev in ("mobile", "desktop"):
        r = cur[(cur["dimension"] == "Device") & (cur["segment"] == dev)].iloc[0]
        p = prev.loc[("Device", dev)]
        facts += [_f("conversion", 100 * r["conversion_rate"], "pct", segment=dev, basis="per_session", label=f"{dev} conversion"),
                  _f("conversion", 100 * (r["conversion_rate"] - p["conversion_rate"]), "pp", "wow", segment=dev,
                     basis="per_session", label=f"{dev} conversion, week on week (points)")]
    end = w + pd.Timedelta(days=6)
    inc = pd.read_csv(PROC / "anomaly_incidents.csv", parse_dates=["first_day", "last_day"])
    inc = inc[(inc["first_day"] <= end) & (inc["last_day"] >= w)]
    opened = inc[inc["status"] == "open: investigate"]
    kpi_metric = {"payment step": "payment_step", "add-to-cart rate": "atc", "conversion rate": "conversion",
                  "shipping step": "shipping_step", "order step": "orders"}
    incidents = []
    for _, r in opened.iterrows():
        m = kpi_metric[r["kpi"]]
        b = "per_session" if m == "conversion" else None
        facts += [_f(m, 100 * r["rate_at_peak"], "pct", segment=r["slice"], basis=b, label=f"{r['kpi']} on {r['slice']}"),
                  _f(m, 100 * r["expected_at_peak"], "pct", "expected", segment=r["slice"], basis=b, label=f"expected {r['kpi']}"),
                  _f(m, 100 * r["rel_change_at_peak"], "pct", "vs_expected", segment=r["slice"], basis=b, label=f"{r['kpi']} vs expected")]
        incidents.append({"slice": r["slice"], "kpi": r["kpi"], "first_day": str(r["first_day"].date()),
                          "candidate_releases": r["candidate_releases"] if isinstance(r["candidate_releases"], str) else ""})
    facts.append(_f("incidents", len(opened), "count", label="incidents opened"))
    mixed = inc[inc["status"].str.startswith("explained: traffic mix")]
    rec = pd.read_csv(PROC / "reconciliation_daily.csv", parse_dates=["d"])
    rw = rec[(rec["d"] >= w) & (rec["d"] <= end)]
    ratio = rw["analytics_revenue_eur"].sum() / rw["shop_revenue_eur"].sum()
    facts.append(_f("revenue", 100 * ratio, "pct", segment="analytics vs shop", basis="gross", label="analytics revenue as % of shop revenue"))
    return {"week_start": week, "data": "SIMULATED", "facts": facts, "incidents": incidents,
            "mix_alerts": int(len(mixed)), "reconciliation_alert": bool(rw["alert"].any())}


def template_draft(sheet: dict) -> str:
    F = {(f["metric"], f["segment"], f["period"], f["unit"], f["basis"]): f["value"] for f in sheet["facts"]}
    g = lambda m, p="current", u="pct", s="All", b=None: F[(m, s, p, u, b)]  # noqa: E731
    w = pd.Timestamp(sheet["week_start"]).strftime("%d %b %Y").lstrip("0")
    s = []
    yoy = f", {g('sessions', 'yoy'):+.1f}% vs the same week last year" if ("sessions", "All", "yoy", "pct", None) in F else ""
    s.append(f"Week of {w}: {g('sessions', u='count'):,.0f} sessions ({g('sessions', 'wow'):+.1f}% week on week{yoy}).")
    s.append(f"Conversion per session was {g('conversion', b='per_session'):.2f}% ({g('conversion', 'wow', 'pp', b='per_session'):+.2f} pp "
             f"week on week, {g('conversion', 'wow', b='per_session'):+.1f}% week on week); per user it was {g('conversion', b='per_user'):.2f}%.")
    recent = pd.Timestamp(sheet["week_start"]) > pd.Timestamp("2026-11-30") - pd.Timedelta(days=100)
    s.append(f"Revenue per visit was €{g('rpv', u='eur', b='gross'):.2f} gross and €{g('rpv', u='eur', b='net'):.2f} net of the returns "
             f"seen so far" + (" (most returns of this week are not visible yet: the trial window is still open)" if recent else "")
             + f"; average order value €{g('aov', u='eur'):.0f}, add-to-cart rate {g('atc'):.2f}%.")
    s.append(f"Mobile conversion per session was {g('conversion', s='mobile', b='per_session'):.2f}% ({g('conversion', 'wow', 'pp', 'mobile', 'per_session'):+.2f} pp "
             f"week on week) while desktop conversion per session was {g('conversion', s='desktop', b='per_session'):.2f}% "
             f"({g('conversion', 'wow', 'pp', 'desktop', 'per_session'):+.2f} pp week on week).")
    n = len(sheet["incidents"])
    if n:
        parts = []
        for i in sheet["incidents"]:
            m = {"payment step": "payment_step", "add-to-cart rate": "atc", "conversion rate": "conversion"}.get(i["kpi"])
            b = "per_session" if m == "conversion" else None
            label = "conversion per session" if m == "conversion" else i["kpi"]
            d = 2 if m == "conversion" else 1
            parts.append(f"{label} on {i['slice']} ran at {g(m, s=i['slice'], b=b):.{d}f}% against an expected "
                         f"{g(m, 'expected', s=i['slice'], b=b):.{d}f}% ({g(m, 'vs_expected', s=i['slice'], b=b):+.1f}% vs expected)")
        s.append(f"Monitoring opened {n} incident{'s' if n > 1 else ''}: " + "; ".join(parts) + ".")
        rel = sorted({r for i in sheet["incidents"] for r in i["candidate_releases"].split(" | ")
                      if "payment" in r.lower() or "carousel" in r.lower()})
        if rel and "payment" in rel[0].lower():
            s.append(f"The release log points to {rel[0]}; next step: reproduce the payment step on an iPhone with "
                     f"Safari, then roll back or hotfix, and pause the reading of any test running on these pages.")
        elif rel:
            s.append(f"The release log points to {rel[0]}; next step: measure the mobile loading time of these pages "
                     f"and resize or lazy-load the new images, then confirm the add-to-cart rate recovers.")
    else:
        s.append("Monitoring opened no incident this week.")
    if sheet["mix_alerts"]:
        s.append("Several funnel alerts this week are explained by a traffic-mix change (more paid-social sessions); "
                 "conversion inside each channel is stable, so no incident was opened.")
    ratio = g("revenue", s="analytics vs shop", u="pct", b="gross")
    s.append(f"Analytics revenue was {ratio:.1f}% of the shop's revenue"
             + (", above the shop: duplicate purchases suspected, de-duplicate on transaction id." if sheet["reconciliation_alert"]
                else ", within the usual range (no duplicate purchases)."))
    return " ".join(s)


def run(week: str) -> tuple[str, check_numbers.Report, str]:
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = build_facts(week)
    llm_text = llm_client.draft(sheet) if llm_client.available() else None
    source, text = ("optional LLM draft", llm_text) if llm_text else ("sentence template", template_draft(sheet))
    rep = check_numbers.check(text, sheet)
    if not rep.passed and source != "sentence template":  # rejected LLM draft -> fall back to the template
        print("LLM draft rejected by the number check:\n" + rep.text())
        source, text = "sentence template", template_draft(sheet)
        rep = check_numbers.check(text, sheet)
    status = "PASS" if rep.passed else "REJECTED"
    md = (f"# Weekly CRO note - week of {week} (SIMULATED store)\n\n"
          f"> Draft source: {source}. Number check: {status} ({sum(f.ok for f in rep.findings)}/{len(rep.findings)} "
          f"numbers traced to the data). To be read and signed off by the analyst before sharing.\n\n{text}\n")
    (OUT / f"weekly_note_{week}.md").write_text(md, encoding="utf-8")
    (OUT / f"weekly_note_{week}.facts.json").write_text(json.dumps(sheet, indent=1), encoding="utf-8")
    return text, rep, source


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", default=DEFAULT_WEEK)
    week = ap.parse_args().week
    text, rep, source = run(week)
    print(f"[{source}] {rep.text()}\n\n{text}")
