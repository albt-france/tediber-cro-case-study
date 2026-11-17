"""Build excel/tediber_cro_toolkit.xlsx (opens in Excel and Google Sheets). Every KPI cell is a formula.

Tabs: Weekly report | Funnel | Anomalies | CRO backlog | Test calculator | Test log, plus the data tabs the
formulas read (data_weekly). Numbers come from the SIMULATED store, except the Test calculator, which is a
generic tool (prefilled with the simulated test D). File metadata (author, last modified by) are left empty.

    python src/build_excel.py           -> builds the workbook
    python src/build_excel.py --verify  -> also recalculates it with LibreOffice (headless) and compares the
                                           key cells with the same calculations done in Python
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import stats_tests as st

ROOT = Path(__file__).resolve().parents[1]
PROC, SIM, OUT = ROOT / "data" / "processed", ROOT / "data" / "sim", ROOT / "excel" / "tediber_cro_toolkit.xlsx"
WEEK = "2026-03-16"

INK, MUTED, BAND, ACCENT = "1F1F1D", "6B6A66", "F2EFE9", "2A78D6"
RED, AMBER, GREEN = "F4C7C6", "FBE3B5", "CFE8D5"
H = Font(name="Segoe UI", bold=True, color=INK, size=11)
TITLE = Font(name="Segoe UI", bold=True, color=INK, size=14)
NOTE = Font(name="Segoe UI", italic=True, color=MUTED, size=9)
BODY = Font(name="Segoe UI", color=INK, size=10)
INPUT = PatternFill("solid", fgColor="FFF8DC")
HEAD = PatternFill("solid", fgColor=BAND)
THIN = Border(bottom=Side(style="thin", color="D9D6CF"))
PCT, PCT1, EUR, INT, PP = "0.00%", "0.0%", '#,##0.00 "€"', "#,##0", '+0.00" pp";-0.00" pp"'


def style_header(ws, row, c1, c2):
    for c in range(c1, c2 + 1):
        cell = ws.cell(row, c)
        cell.font, cell.fill, cell.border = H, HEAD, THIN
        cell.alignment = Alignment(wrap_text=True, vertical="center")


def put(ws, ref, value, fmt=None, font=BODY, fill=None):
    ws[ref] = value
    ws[ref].font = font
    if fmt:
        ws[ref].number_format = fmt
    if fill:
        ws[ref].fill = fill
    return ws[ref]


def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[get_column_letter(i)].width = x


# ---------------------------------------------------------------- data tab
def weekly_data() -> pd.DataFrame:
    s = pd.read_parquet(SIM / "sessions_daily.parquet")
    o = pd.read_parquet(SIM / "orders.parquet")
    s["week"] = s["date"].dt.to_period("W-SUN").dt.start_time
    o["week"] = o["date"].dt.to_period("W-SUN").dt.start_time
    o["returned_eur"] = o["basket_eur"].where(o["returned"], 0)
    cols = ["sessions", "users", "add_to_cart", "checkout_starts", "orders", "revenue_eur"]
    frames = []
    for seg_col in (None, "device"):
        g = s.groupby(["week"] + ([seg_col] if seg_col else []))[cols].sum().reset_index()
        r = o.groupby(["week"] + ([seg_col] if seg_col else []))["returned_eur"].sum().reset_index()
        g = g.merge(r, how="left").fillna({"returned_eur": 0})
        g["segment"] = g[seg_col] if seg_col else "All"
        frames.append(g.drop(columns=[seg_col]) if seg_col else g)
    d = pd.concat(frames)
    days = s.groupby("week")["date"].nunique()
    d = d[d["week"].map(days) == 7]
    return d[["week", "segment"] + cols + ["returned_eur"]].sort_values(["week", "segment"]).reset_index(drop=True)


def sheet_data(wb, d):
    ws = wb.create_sheet("data_weekly")
    head = ["week_start", "segment", "sessions", "users", "add_to_cart", "checkout_starts", "orders", "revenue_eur",
            "returned_revenue_eur"]
    ws.append(head)
    style_header(ws, 1, 1, len(head))
    for r in d.itertuples(index=False):
        ws.append([r.week.to_pydatetime(), r.segment, int(r.sessions), int(r.users), int(r.add_to_cart),
                   int(r.checkout_starts), int(r.orders), round(float(r.revenue_eur), 2), round(float(r.returned_eur), 2)])
    for row in ws.iter_rows(min_row=2, min_col=1, max_col=1):
        row[0].number_format = "yyyy-mm-dd"
    widths(ws, [12, 10, 10, 10, 12, 14, 9, 13, 18])
    ws.freeze_panes = "A2"
    put(ws, "K1", "SIMULATED store - weekly sums from data/sim (Monday weeks). Returns are attached to the week of the order "
                  "and only those observed by 30 Nov 2026 are counted.", font=NOTE)
    return len(d) + 1


# ---------------------------------------------------------------- 1. weekly report
def sheet_weekly(wb, n_data):
    ws = wb.create_sheet("Weekly report", 0)
    widths(ws, [2, 30, 15, 15, 14, 15, 14, 12, 4, 46])
    put(ws, "B2", "Weekly CRO report", font=TITLE)
    put(ws, "B3", "SIMULATED store modelled on public information - not Tediber's data. Pick a week (Monday) in C5.", font=NOTE)
    put(ws, "B5", "Week starting (Monday)", font=H)
    c = put(ws, "C5", datetime.fromisoformat(WEEK), "yyyy-mm-dd", font=H, fill=INPUT)
    dv = DataValidation(type="list", formula1=f"=data_weekly!$A$2:$A${n_data}", allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(c)
    put(ws, "B6", "Alert thresholds (relative change)", font=BODY)
    put(ws, "C6", -0.05, PCT1, fill=INPUT)
    put(ws, "D6", "red at or below", font=NOTE)
    put(ws, "E6", -0.02, PCT1, fill=INPUT)
    put(ws, "F6", "amber at or below", font=NOTE)

    R = lambda col: f"data_weekly!${col}$2:${col}${n_data}"  # noqa: E731
    COL = {"sessions": "C", "users": "D", "atc": "E", "chk": "F", "orders": "G", "rev": "H", "ret": "I"}

    def s(metric, week_expr, seg='"All"'):
        return f'SUMIFS({R(COL[metric])},{R("A")},{week_expr},{R("B")},{seg})'

    weeks = {"C": "$C$5", "D": "$C$5-7", "F": "$C$5-364"}
    head = ["KPI", "This week", "Previous week", "Week on week", "Same week last year", "Year on year", "Status"]
    for i, h in enumerate(head):
        ws.cell(8, 2 + i, h)
    style_header(ws, 8, 2, 8)
    kpis = [  # label, formula builder(week expr), number format, "higher is better"
        ("Sessions", lambda w: s("sessions", w), INT, True),
        ("Orders", lambda w: s("orders", w), INT, True),
        ("Conversion rate (per session)", lambda w: f"{s('orders', w)}/{s('sessions', w)}", PCT, True),
        ("Conversion rate (per user)", lambda w: f"{s('orders', w)}/{s('users', w)}", PCT, True),
        ("Average order value", lambda w: f"{s('rev', w)}/{s('orders', w)}", EUR, True),
        ("Revenue per visit (gross)", lambda w: f"{s('rev', w)}/{s('sessions', w)}", EUR, True),
        ("Revenue per visit (net of returns)", lambda w: f"({s('rev', w)}-{s('ret', w)})/{s('sessions', w)}", EUR, True),
        ("Add-to-cart rate (sessions)", lambda w: f"{s('atc', w)}/{s('sessions', w)}", PCT, True),
        ("Checkout abandonment", lambda w: f"1-{s('orders', w)}/{s('chk', w)}", PCT, False),
    ]
    for i, (label, f, fmt, up) in enumerate(kpis):
        r = 9 + i
        put(ws, f"B{r}", label)
        for col, wexpr in weeks.items():
            put(ws, f"{col}{r}", f"=IFERROR({f(wexpr)},\"\")", fmt)
        put(ws, f"E{r}", f'=IFERROR(C{r}/D{r}-1,"")', PCT1)
        put(ws, f"G{r}", f'=IFERROR(C{r}/F{r}-1,"")', PCT1)
        sign = "" if up else "-"
        put(ws, f"H{r}", f'=IF(E{r}="","",IF({sign}E{r}<=$C$6,"RED",IF({sign}E{r}<=$E$6,"AMBER","GREEN")))')
    last = 9 + len(kpis) - 1
    for txt, color in (("RED", RED), ("AMBER", AMBER), ("GREEN", GREEN)):
        ws.conditional_formatting.add(f"H9:H{last}", CellIsRule(operator="equal", formula=[f'"{txt}"'],
                                                                 fill=PatternFill("solid", fgColor=color)))
    r0 = last + 2
    put(ws, f"B{r0}", "Conversion by device", font=H)
    for i, h in enumerate(["Device", "This week", "Previous week", "Change (pp)"]):
        ws.cell(r0 + 1, 2 + i, h)
    style_header(ws, r0 + 1, 2, 5)
    for i, dev in enumerate(("mobile", "desktop", "tablet")):
        r = r0 + 2 + i
        put(ws, f"B{r}", dev)
        for col, wexpr in (("C", "$C$5"), ("D", "$C$5-7")):
            put(ws, f"{col}{r}", f'=IFERROR({s("orders", wexpr, chr(34) + dev + chr(34))}/{s("sessions", wexpr, chr(34) + dev + chr(34))},"")', PCT)
        put(ws, f"E{r}", f'=IFERROR((C{r}-D{r})*100,"")', PP)
    put(ws, "J8", "3 findings and 3 actions (week of 16 Mar 2026)", font=H)
    ws["J8"].fill = HEAD
    notes = [
        "Finding 1 - Payment step on mobile Safari iOS fell to ~64% vs ~83% expected; other browsers stable.",
        "Finding 2 - The drop starts right after the 10 Mar release of the split-payment widget (release log).",
        "Finding 3 - Topline conversion barely moves (-1%): the break hides in one segment; a topline-only "
        "report would have missed it.",
        "Action 1 - Reproduce on an iPhone with Safari; ask Tech to roll back or hotfix the widget (owner: Tech).",
        "Action 2 - Exclude the affected days from any A/B test reading on checkout pages (owner: CRO).",
        "Action 3 - Add a Safari iOS payment check to the pre-release QA checklist (owner: CRO + QA).",
    ]
    for i, t in enumerate(notes):
        c = put(ws, f"J{9 + i}", t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[9 + i].height = 30
    put(ws, f"J{9 + len(notes) + 1}", "These notes are written for the default week; KPI cells update with C5.", font=NOTE)
    ws.freeze_panes = "B9"


# ---------------------------------------------------------------- 2. funnel
def sheet_funnel(wb):
    ws = wb.create_sheet("Funnel")
    f = pd.read_csv(PROC / "funnel_segments.csv")
    f = f[f["dimension"].isin(["All", "Device", "Category", "Visitor type", "Channel"])]
    widths(ws, [2, 14, 18] + [12] * 8 + [3] + [11] * 6)
    put(ws, "B2", "Funnel by segment, whole period (SIMULATED store)", font=TITLE)
    put(ws, "B3", "Counts = sessions that reached each step. Pass rates are formulas (step / previous step).", font=NOTE)
    head = ["Dimension", "Segment", "Sessions", "Product views", "Add to cart", "Checkout", "Shipping done",
            "Payment done", "Orders", "Conversion", "", "Product view", "Add to cart", "Checkout", "Shipping",
            "Payment", "Order"]
    for i, h in enumerate(head):
        ws.cell(5, 2 + i, h)
    style_header(ws, 5, 2, 1 + len(head))
    for i, r in enumerate(f.itertuples(index=False)):
        row = 6 + i
        vals = [r.dimension, r.segment, r.sessions, r.product_views, r.add_to_cart, r.checkout_starts,
                r.shipping_completed, r.payment_completed, r.orders]
        for j, v in enumerate(vals):
            put(ws, f"{get_column_letter(2 + j)}{row}", int(v) if j >= 2 else v, INT if j >= 2 else None)
        put(ws, f"K{row}", f"=J{row}/D{row}", PCT)
        for j, (num, den) in enumerate(zip("EFGHIJ", "DEFGHI")):
            put(ws, f"{get_column_letter(13 + j)}{row}", f"={num}{row}/{den}{row}", PCT1)
    last = 5 + len(f)
    ws.conditional_formatting.add(f"P6:P{last}", CellIsRule(operator="lessThan", formula=["0.7"],
                                                            fill=PatternFill("solid", fgColor=RED)))
    put(ws, f"B{last + 2}", "Read: shipping-step pass rate is ~60% for bed bases & beds and sofas vs ~80% elsewhere: "
                            "abandonment at the delivery step is twice as high for bulky items (hypothesis: the delivery fee "
                            "appears only at checkout).", font=NOTE)
    ch = BarChart()
    ch.type, ch.title, ch.y_axis.title = "bar", "Shipping-step pass rate by category", "pass rate"
    cats = [i for i, r in enumerate(f.itertuples()) if r.dimension == "Category"]
    a, b = 6 + cats[0], 6 + cats[-1]
    ch.add_data(Reference(ws, min_col=16, min_row=a, max_row=b), titles_from_data=False)
    ch.set_categories(Reference(ws, min_col=3, min_row=a, max_row=b))
    ch.legend, ch.height, ch.width = None, 7, 14
    ws.add_chart(ch, f"B{last + 4}")
    ws.freeze_panes = "D6"


# ---------------------------------------------------------------- 3. anomalies
def sheet_anomalies(wb):
    ws = wb.create_sheet("Anomalies")
    widths(ws, [2, 12, 12, 22, 22, 12, 9, 52, 30, 16])
    put(ws, "B2", "Anomaly log (SIMULATED store)", font=TITLE)
    put(ws, "B3", "Alerts from sql/03_anomalies.sql and sql/04_reconciliation.sql, plus the test and funnel checks. "
                  "Cause = release log + segmentation, confirmed by a human.", font=NOTE)
    head = ["First day", "Last day", "KPI", "Segment", "Change vs expected", "Robust z", "Likely cause (evidence)",
            "Status", "Owner"]
    for i, h in enumerate(head):
        ws.cell(5, 2 + i, h)
    style_header(ws, 5, 2, 10)
    inc = pd.read_csv(PROC / "anomaly_incidents.csv")
    rec = pd.read_csv(PROC / "reconciliation_incidents.csv")
    ro = pd.read_csv(PROC / "experiment_readout.csv").set_index("test_id")
    rows = []
    for r in inc.itertuples(index=False):
        if r.status == "open: investigate":
            cause = ("Split-payment widget release of 10 Mar (Safari iOS only)" if "Safari" in r.slice else
                     "Mattress image carousel of 12 May: mobile LCP +1.4 s, desktop not affected")
            owner = "Tech + CRO"
        else:
            cause, owner = "More paid-social sessions (channel mix); conversion stable inside each channel", "Acquisition (info)"
        rows.append([r.first_day, r.last_day, r.kpi, r.slice, r.rel_change_at_peak, r.z_at_peak, cause, r.status, owner])
    for r in rec.itertuples(index=False):
        rows.append([r.first_day, r.last_day, "analytics vs shop revenue", "all", r.max_revenue_ratio - 1, None,
                     "Purchase tag migrated on 7 Jul fired twice; fixed 4 Aug. Rule: de-duplicate on transaction id",
                     "closed: fixed", "Data / Tech"])
    b = ro.loc["B"]
    rows.append(["2026-04-06", "2026-05-03", "test allocation", "test B", b["variant_share"] - 0.5, None,
                 f"Sample ratio mismatch {b['variant_share']:.1%} variant (chi-square p < 0.001): redirect drops visitors",
                 "test invalidated", "CRO + Tech"])
    rows.append(["whole period", "", "shipping step", "Bed base & bed, Sofa", -0.25, None,
                 "Structural: abandonment at the delivery step twice the other categories (fee shown at checkout)",
                 "backlog: test C", "CRO"])
    rows.append(["2026-11-01", "2026-11-30", "sessions, conversion", "all", None, None,
                 "Black Month: traffic x2, conversion up, basket down - compared with Black Month 2025, no alert",
                 "expected (promo calendar)", "-"])
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            cell = put(ws, f"{get_column_letter(2 + j)}{6 + i}", v)
            if j == 4 and v is not None:
                cell.number_format = PCT1
            if j == 5 and v is not None:
                cell.number_format = "0.0"
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    last = 5 + len(rows)
    ws.conditional_formatting.add(f"I6:I{last}", FormulaRule(formula=['LEFT($I6,4)="open"'], fill=PatternFill("solid", fgColor=RED)))
    ws.conditional_formatting.add(f"I6:I{last}", FormulaRule(formula=['LEFT($I6,9)="explained"'], fill=PatternFill("solid", fgColor=GREEN)))
    ws.freeze_panes = "B6"


# ---------------------------------------------------------------- 4. backlog
BACKLOG = [  # idea, page, source, evidence, reach/qtr, impact(0.25-3), confidence, effort (p-w), ICE I, C, E, seen on Tediber's public pages
    ("Show the delivery fee of bulky items on the product page", "Product page (bulky)", "Data (sim)", "Shipping-step abandonment x2 on bulky items in the simulated store", 160000, 2, 0.8, 2, 8, 8, 7, "Yes: delivery options and fees on the bed-base page"),
    ("Sticky add-to-cart button on mobile product pages", "Product page", "Benchmark + data (sim)", "Mobile add-to-cart below desktop in the simulated store", 280000, 1, 0.8, 1, 6, 8, 9, "Yes: sticky bar on the mattress page (mobile)"),
    ("Comparator v2: firmness / sleep-position guidance, judged on net revenue", "Mattress pages", "Test D (sim)", "Comparator +8% conversion but more 100-night returns", 300000, 2, 0.5, 4, 7, 5, 4, "Partly: comparator and quiz exist; effect on returns not observable"),
    ("Relaunch the '100-night trial' block next to the button (no redirect)", "Product page", "Test B (sim, invalid)", "First run broken by a redirect (SRM)", 400000, 1, 0.5, 1, 5, 5, 9, "Yes: trial and free returns listed under the button"),
    ("Mobile performance budget: images and third-party scripts", "All pages", "Lighthouse (public)", "Lab mobile LCP 6.8 s or more and blocking time above 1 s on every page measured", 420000, 1, 0.6, 3, 6, 6, 5, "Opportunity: measured on public pages (lab data, confirm with real-user data)"),
    ("One split-payment message everywhere", "Banner, home, product page", "UX audit (public)", "Banner says 3x to 24x; engagement blocks and product page say 3x to 12x", 450000, 0.5, 0.6, 0.5, 4, 6, 10, "Opportunity: two ranges displayed on 17 Nov 2026"),
    ("Delivery promise adapted on bulky-item pages (banner '48h' vs 8-10 days)", "Bed-base, sofa pages", "UX audit (public)", "The '48h' banner also shows on the bed-base page; bulky delivery takes 8-10 days per the delivery page", 160000, 1, 0.6, 1, 6, 6, 8, "Opportunity: banner identical on all pages"),
    ("Trial-period e-mails (sleep tips, adjustment) to reduce returns", "CRM", "Test D (sim)", "Returns are the main gap between gross and net revenue for mattresses", 50000, 1, 0.5, 2, 6, 5, 6, "Not observable from public pages"),
    ("Dedicated landing pages for cold paid-social traffic", "Landing pages", "Data (sim)", "Paid social converts ~0.4% vs ~1.2% average; the mix pulled the topline down in Sep", 180000, 1, 0.5, 3, 6, 5, 4, "Not observable from public pages"),
    ("Carry the quiz result to the product page (recommended model and firmness)", "Category -> product", "UX audit (public)", "Quiz 'Quel matelas choisir ?' sits on the category page", 250000, 1, 0.5, 2, 6, 5, 6, "Partly: quiz on the mattress category page"),
    ("'Try it in store' block on mattress pages (Paris, Lyon, Toulouse)", "Mattress pages", "Public site", "4 stores on the store locator; not seen in our mobile capture of the mattress page", 120000, 0.5, 0.5, 1, 4, 5, 8, "Not seen in our capture"),
    ("Saving in euros on bed packs vs items bought separately", "Pack pages", "UX audit (public)", "94 pack product URLs in the sitemap; packs promoted in % during Black Month", 90000, 1, 0.5, 1, 5, 5, 8, "Partly: % discount shown"),
    ("Checkout-abandonment e-mail with trial and returns reminder", "CRM", "Benchmark", "Checkout abandonment ~56% in the real GA4 sample", 60000, 1, 0.6, 2, 6, 6, 6, "Not observable (checkout not visited)"),
    ("Compact consent banner on mobile (test with the legal team)", "All pages (mobile)", "UX audit (public)", "Consent panel covers most of the mobile screen in our capture", 300000, 0.5, 0.4, 1, 4, 4, 7, "Observed in a headless capture: to confirm on a real phone"),
    ("Pre-release QA checklist: payment on Safari iOS (not a test)", "Process", "Data (sim)", "9-day payment break on Safari iOS after a widget release", 0, 0, 1, 0.5, 9, 9, 10, "Process"),
    ("Purchase-tag monitoring alert (not a test)", "Process", "Data (real + sim)", "Duplicate purchase events: +7.4% revenue in the real GA4 sample, ~+10% in the simulated incident", 0, 0, 1, 0.5, 8, 9, 9, "Process"),
    ("Free returns and trial reminder in the cart", "Cart", "Benchmark", "Not observed (cart not visited): to verify with the team", 200000, 0.5, 0.4, 1, 4, 4, 8, "Not observable (cart not visited)"),
    ("Size guide next to the size selector on mattress pages", "Mattress pages", "Benchmark", "Size is the first choice on the page; wrong size is a return reason in general", 300000, 0.5, 0.5, 1, 4, 5, 8, "Not checked"),
]


def sheet_backlog(wb):
    ws = wb.create_sheet("CRO backlog")
    widths(ws, [2, 5, 46, 20, 16, 44, 11, 9, 11, 9, 7, 7, 7, 8, 11, 8, 8, 40])
    put(ws, "B2", "Prioritised CRO backlog - ICE and RICE", font=TITLE)
    put(ws, "B3", "ICE = Impact x Confidence x Ease (each 1-10). RICE = Reach x Impact x Confidence / Effort "
                  "(reach = eligible visitors per quarter, impact 0.25-3, confidence %, effort in person-weeks). "
                  "Yellow cells are inputs; scores and ranks are formulas. Process items have reach 0 (do them anyway). "
                  "Reach and scores refer to the SIMULATED store; column R says what Tediber's public pages already show.", font=NOTE)
    head = ["ID", "Idea", "Page", "Source", "Evidence", "Reach / qtr", "Impact", "Confidence", "Effort (p-w)",
            "ICE I", "ICE C", "ICE E", "ICE", "RICE", "ICE rank", "RICE rank",
            "Seen on Tediber's public pages (17 Nov 2026)"]
    for i, h in enumerate(head):
        ws.cell(5, 2 + i, h)
    style_header(ws, 5, 2, 18)
    n = len(BACKLOG)
    last = 5 + n
    for i, (idea, page, src, ev, reach, imp, conf, eff, ii, ic, ie, seen) in enumerate(BACKLOG):
        r = 6 + i
        put(ws, f"B{r}", f"B{i + 1:02d}")
        put(ws, f"R{r}", seen).alignment = Alignment(wrap_text=True, vertical="top")
        for col, v in zip("CDEF", (idea, page, src, ev)):
            put(ws, f"{col}{r}", v).alignment = Alignment(wrap_text=True, vertical="top")
        for col, v, fmt in (("G", reach, INT), ("H", imp, "0.00"), ("I", conf, "0%"), ("J", eff, "0.0"),
                            ("K", ii, "0"), ("L", ic, "0"), ("M", ie, "0")):
            put(ws, f"{col}{r}", v, fmt, fill=INPUT)
        put(ws, f"N{r}", f"=K{r}*L{r}*M{r}", "0")
        put(ws, f"O{r}", f"=G{r}*H{r}*I{r}/J{r}", INT)
        # rank with a tie-breaker on the row order, so every rank is unique
        put(ws, f"P{r}", f"=RANK(N{r},$N$6:$N${last})+COUNTIF($N$6:N{r},N{r})-1", "0")
        put(ws, f"Q{r}", f"=RANK(O{r},$O$6:$O${last})+COUNTIF($O$6:O{r},O{r})-1", "0")
        ws.row_dimensions[r].height = 30
    t = last + 2
    put(ws, f"B{t}", "Top 5 by RICE (formula: looks up ranks 1 to 5)", font=H)
    for k in range(5):
        r = t + 1 + k
        put(ws, f"B{r}", k + 1)
        put(ws, f"C{r}", f"=INDEX($C$6:$C${last},MATCH({k + 1},$Q$6:$Q${last},0))")
        put(ws, f"G{r}", f"=INDEX($O$6:$O${last},MATCH({k + 1},$Q$6:$Q${last},0))", INT)
        put(ws, f"N{r}", f"=INDEX($N$6:$N${last},MATCH({k + 1},$Q$6:$Q${last},0))", "0")
    put(ws, f"H{t + 1}", "<- RICE", font=NOTE)
    put(ws, f"O{t + 1}", "<- ICE", font=NOTE)
    ws.freeze_panes = "D6"


# ---------------------------------------------------------------- 5. test calculator
def sheet_calculator(wb, ro):
    ws = wb.create_sheet("Test calculator")
    widths(ws, [2, 46, 16, 4, 46, 16])
    put(ws, "B2", "A/B test calculator", font=TITLE)
    put(ws, "B3", "Yellow = inputs. Two-sided test on proportions. Prefilled with test D (SIMULATED) and the SRM of test B.", font=NOTE)
    put(ws, "B5", "1. Before launch: sample size and duration", font=H)
    rows = [("Baseline conversion rate", 0.016, "0.00%", True), ("Minimum detectable effect (relative)", 0.08, "0%", True),
            ("Significance level (alpha)", 0.05, "0%", True), ("Power", 0.80, "0%", True),
            ("Eligible visitors per day (all variants)", 6000, INT, True), ("Number of variants (incl. control)", 2, "0", True)]
    for i, (lab, v, fmt, inp) in enumerate(rows):
        put(ws, f"B{6 + i}", lab)
        put(ws, f"C{6 + i}", v, fmt, fill=INPUT if inp else None)
    put(ws, "B12", "Target conversion rate")
    put(ws, "C12", "=C6*(1+C7)", "0.000%")
    put(ws, "B13", "Visitors needed per variant")
    put(ws, "C13", "=ROUNDUP((_xlfn.NORM.S.INV(1-C8/2)+_xlfn.NORM.S.INV(C9))^2*(C6*(1-C6)+C12*(1-C12))/(C12-C6)^2,0)", INT, font=H)
    put(ws, "B14", "Days needed (rounded up to whole weeks)")
    put(ws, "C14", "=CEILING(C13*C11/C10,7)", "0", font=H)
    put(ws, "B15", "Rule: decide the duration before launch and do not stop at the first significant day (peeking).", font=NOTE)

    d = ro.set_index("test_id").loc["D"]
    s = pd.read_csv(PROC / "experiment_summary.csv").set_index(["test_id", "variant"])
    put(ws, "E5", "2. After the test: read the result", font=H)
    vals = [("Visitors - control", int(s.loc[("D", "control"), "visitors"])),
            ("Conversions - control", int(s.loc[("D", "control"), "orders"])),
            ("Visitors - variant", int(s.loc[("D", "variant"), "visitors"])),
            ("Conversions - variant", int(s.loc[("D", "variant"), "orders"]))]
    for i, (lab, v) in enumerate(vals):
        put(ws, f"E{6 + i}", lab)
        put(ws, f"F{6 + i}", v, INT, fill=INPUT)
    out = [("Conversion - control", "=F7/F6", "0.000%"), ("Conversion - variant", "=F9/F8", "0.000%"),
           ("Relative lift", "=F11/F10-1", "0.0%"), ("Pooled rate", "=(F7+F9)/(F6+F8)", "0.000%"),
           ("z", "=(F11-F10)/SQRT(F13*(1-F13)*(1/F6+1/F8))", "0.00"),
           ("p-value (two-sided)", "=2*(1-_xlfn.NORM.S.DIST(ABS(F14),TRUE))", "0.0000"),
           ("95% CI of the difference - low", "=(F11-F10)-_xlfn.NORM.S.INV(0.975)*SQRT(F10*(1-F10)/F6+F11*(1-F11)/F8)", "0.000%"),
           ("95% CI of the difference - high", "=(F11-F10)+_xlfn.NORM.S.INV(0.975)*SQRT(F10*(1-F10)/F6+F11*(1-F11)/F8)", "0.000%"),
           ("Significant at alpha?", '=IF(F15<C8,"yes","no")', None)]
    for i, (lab, f, fmt) in enumerate(out):
        put(ws, f"E{10 + i}", lab)
        put(ws, f"F{10 + i}", f, fmt)
    put(ws, "E19", "Then check the guardrails (net revenue per visitor, 100-night returns) before deciding: "
                   f"for test D, net revenue per visitor {d['rpv_net_lift']:+.1%} [{d['rpv_net_ci_low']:+.1%}; "
                   f"{d['rpv_net_ci_high']:+.1%}] -> iterate.", font=NOTE)
    put(ws, "E21", "3. Sample ratio mismatch (SRM) - check FIRST", font=H)
    b = s.loc["B"]
    put(ws, "E22", "Visitors - control")
    put(ws, "F22", int(b.loc["control", "visitors"]), INT, fill=INPUT)
    put(ws, "E23", "Visitors - variant")
    put(ws, "F23", int(b.loc["variant", "visitors"]), INT, fill=INPUT)
    put(ws, "E24", "Planned share of the variant")
    put(ws, "F24", 0.5, "0%", fill=INPUT)
    put(ws, "E25", "Observed share of the variant")
    put(ws, "F25", "=F23/(F22+F23)", "0.00%")
    put(ws, "E26", "Chi-square (1 degree of freedom)")
    put(ws, "F26", "=(F22-(F22+F23)*(1-F24))^2/((F22+F23)*(1-F24))+(F23-(F22+F23)*F24)^2/((F22+F23)*F24)", "0.0")
    put(ws, "E27", "p-value")
    put(ws, "F27", "=_xlfn.CHISQ.DIST.RT(F26,1)", "0.00E+00")
    put(ws, "E28", "Verdict")
    put(ws, "F28", '=IF(F27<0.001,"SRM - do not read the test","allocation OK")', font=H)


# ---------------------------------------------------------------- 6. test log
def sheet_testlog(wb, ro):
    ws = wb.create_sheet("Test log")
    widths(ws, [2, 6, 44, 18, 12, 11, 11, 11, 12, 13, 14, 26, 50])
    put(ws, "B2", "Test log (SIMULATED store)", font=TITLE)
    plan = pd.read_csv(PROC / "power_plan.csv").set_index("test_id")
    s = pd.read_csv(PROC / "experiment_summary.csv").groupby("test_id").agg(start=("start_date", "min"), end=("end_date", "max"))
    head = ["ID", "Test", "Primary KPI", "Start", "Variant share", "Primary lift", "p-value", "Net RPV lift",
            "Return rate (ctl / var)", "Planned MDE", "Decision", "Learning"]
    for i, h in enumerate(head):
        ws.cell(4, 2 + i, h)
    style_header(ws, 4, 2, 13)
    learn = {"A": "Keeping the button in view helps mobile visitors add to cart; no guardrail harmed.",
             "B": "A redirect-based variant loses visitors: build variants client-side; relaunch.",
             "C": "Showing the bulky delivery fee early costs some add-to-carts but wins at checkout.",
             "D": "Helping people choose raises conversion, but some choose wrong: add firmness guidance, retest on net RPV."}
    for i, r in enumerate(ro.itertuples(index=False)):
        row = 5 + i
        vals = [r.test_id, r.test_name, r.primary_kpi, s.loc[r.test_id, "start"], r.variant_share, r.primary_lift,
                r.primary_p_value, r.rpv_net_lift, f"{r.return_rate_control:.1%} / {r.return_rate_variant:.1%}",
                plan.loc[r.test_id, "mde_relative"], r.decision, learn[r.test_id]]
        fmts = [None, None, None, None, "0.0%", "+0.0%;-0.0%", "0.0000", "+0.0%;-0.0%", None, "0%", None, None]
        for j, (v, fmt) in enumerate(zip(vals, fmts)):
            cell = put(ws, f"{get_column_letter(2 + j)}{row}", v, fmt)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[row].height = 32
    put(ws, "B10", "Decision rule (written before launch): SRM -> invalid; primary up (p < 0.05) and no guardrail breached "
                   "-> ship; primary up but returns up (p < 0.05) or net RPV clearly down -> iterate; otherwise drop.", font=NOTE)


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)
    d = weekly_data()
    n = sheet_data(wb, d)
    ro = pd.read_csv(PROC / "experiment_readout.csv")
    sheet_weekly(wb, n)
    sheet_funnel(wb)
    sheet_anomalies(wb)
    sheet_backlog(wb)
    sheet_calculator(wb, ro)
    sheet_testlog(wb, ro)
    wb.move_sheet("data_weekly", offset=len(wb.sheetnames))
    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
    wb.properties.creator = ""
    wb.properties.lastModifiedBy = ""
    wb.properties.title = "CRO toolkit - case study"
    wb.save(OUT)
    print(f"written {OUT.relative_to(ROOT)}")


def verify() -> bool:
    """Recalculate with LibreOffice (headless) and compare key cells with Python."""
    soffice = shutil.which("soffice") or r"C:\Program Files\LibreOffice\program\soffice.exe"
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([soffice, "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(tmp), str(OUT)],
                   check=True, capture_output=True, timeout=180)
    wb = load_workbook(tmp / OUT.name, data_only=True)
    d = weekly_data()
    w = d[(d["week"] == WEEK) & (d["segment"] == "All")].iloc[0]
    p = d[(d["week"] == pd.Timestamp(WEEK) - pd.Timedelta(days=7)) & (d["segment"] == "All")].iloc[0]
    wr, calc, bl = wb["Weekly report"], wb["Test calculator"], wb["CRO backlog"]
    srm = st.srm_check(calc["F22"].value, calc["F23"].value)
    tp = st.two_proportion_test(calc["F7"].value, calc["F6"].value, calc["F9"].value, calc["F8"].value)
    checks = [
        ("sessions this week", wr["C9"].value, w["sessions"]),
        ("conversion this week", wr["C11"].value, w["orders"] / w["sessions"]),
        ("conversion per user", wr["C12"].value, w["orders"] / w["users"]),
        ("net RPV", wr["C15"].value, (w["revenue_eur"] - w["returned_eur"]) / w["sessions"]),
        ("conversion WoW", wr["E11"].value, (w["orders"] / w["sessions"]) / (p["orders"] / p["sessions"]) - 1),
        ("sample size per arm", calc["C13"].value, st.sample_size_per_arm(0.016, 0.08)),
        ("z", calc["F14"].value, tp["z"]),
        ("p-value", calc["F15"].value, tp["p_value"]),
        ("CI low", calc["F16"].value, tp["ci_diff_low"]),
        ("SRM chi-square", calc["F26"].value, srm["chi2"]),
        ("SRM p-value", calc["F27"].value, srm["p_value"]),
        ("ICE of B01", bl["N6"].value, 8 * 8 * 7),
        ("RICE of B01", bl["O6"].value, 160000 * 2 * 0.8 / 2),
    ]
    ok = True
    for name, got, want in checks:
        good = got is not None and abs(float(got) - float(want)) <= 1e-6 * max(1, abs(float(want))) + 1e-12
        ok &= good
        print(f"  {'OK ' if good else 'BAD'} {name:22s} excel={got}  python={want}")
    top = [bl[f"C{5 + len(BACKLOG) + 3 + k}"].value for k in range(5)]
    print("  top 5 by RICE:", top)
    ok &= None not in top
    shutil.rmtree(tmp, ignore_errors=True)
    return ok


if __name__ == "__main__":
    build()
    if "--verify" in sys.argv:
        good = verify()
        print("verification:", "PASS" if good else "FAIL")
        sys.exit(0 if good else 1)
