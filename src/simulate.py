"""SIMULATED data: a DTC bedding store modelled on public information (NOT Tediber's data).

18 months, day by day (1 Jun 2025 - 30 Nov 2026), seed 42. Sessions are aggregated per
day x device x browser x channel x visitor type x entry category (no row per session).
Orders are drawn per cell, then given a basket value, a split-payment flag and a 100-night return outcome.
Calibration (orders of magnitude only, see data/ASSUMPTIONS.md):
- volume: ~3.5 M sessions a year, consistent with the 2020 revenue published in the French company register
  (EUR 23.6 M) and an average basket of a few hundred euros;
- funnel step rates and device mix: the real GA4 sample (Google Merchandise Store) and public benchmarks;
- prices: ranges read on public product pages; seasonality: sales periods and a November "Black Month".
Eight events are planted (data/_hidden_truth.csv, used once to score the detection, never committed).

    python src/simulate.py      -> data/sim/*.parquet (+ data/_hidden_truth.csv)
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "data" / "sim"
rng = np.random.default_rng(42)
START, END = pd.Timestamp("2025-06-01"), pd.Timestamp("2026-11-30")
AS_OF = END  # returns after this date are not observed yet
DAYS = pd.date_range(START, END, freq="D")

# ------------------------------------------------------------------ segments and shares
DEVICE = {"mobile": 0.60, "desktop": 0.34, "tablet": 0.06}
BROWSER = {"mobile": {"Safari iOS": 0.52, "Chrome": 0.42, "Other": 0.06},
           "tablet": {"Safari iOS": 0.60, "Chrome": 0.30, "Other": 0.10},
           "desktop": {"Chrome": 0.68, "Other": 0.32}}
CHANNEL = {"Organic search": 0.28, "Paid search": 0.22, "Paid social": 0.14, "Email / CRM": 0.10,
           "Direct": 0.17, "Affiliation": 0.09}
RETURNING = {"Organic search": 0.25, "Paid search": 0.20, "Paid social": 0.12, "Email / CRM": 0.70,
             "Direct": 0.55, "Affiliation": 0.20}
CATEGORY = {"Mattress": 0.38, "Bed base & bed": 0.16, "Pillow & duvet": 0.22, "Bed linen": 0.12,
            "Kids": 0.07, "Sofa": 0.05}
BULKY = {"Bed base & bed", "Sofa"}

# ------------------------------------------------------------------ funnel (session level)
P = {"category_view": 0.60, "pdp_view": 0.48, "atc_given_pdp": 0.068, "cart_given_atc": 0.88,
     "checkout_given_atc": 0.58, "shipping_given_checkout": 0.80, "payment_given_shipping": 0.82,
     "order_given_payment": 0.80}
F_ATC = {"device": {"mobile": 0.85, "desktop": 1.18, "tablet": 1.0},
         "browser": {"Safari iOS": 1.0, "Chrome": 1.0, "Other": 0.95},
         "channel": {"Organic search": 1.0, "Paid search": 1.15, "Paid social": 0.45, "Email / CRM": 1.5,
                     "Direct": 1.3, "Affiliation": 1.35},
         "visitor": {"New": 1.0, "Returning": 1.55},
         "category": {"Mattress": 0.65, "Bed base & bed": 0.80, "Pillow & duvet": 1.35, "Bed linen": 1.45,
                      "Kids": 1.10, "Sofa": 0.55}}
F_CHK = {"device": {"mobile": 0.92, "desktop": 1.08, "tablet": 1.0}, "visitor": {"New": 1.0, "Returning": 1.12}}
SHIPPING_BULKY = 0.75  # delivery fees for bulky items appear at the shipping step: abandonment 20% -> 40%
AOV = {"Mattress": 780, "Bed base & bed": 620, "Pillow & duvet": 165, "Bed linen": 120, "Kids": 330, "Sofa": 1350}
RETURN_RATE = {"Mattress": 0.085, "Bed base & bed": 0.04, "Pillow & duvet": 0.05, "Bed linen": 0.03,
               "Kids": 0.045, "Sofa": 0.06}
SESSIONS_PER_USER = {"New": 1.15, "Returning": 1.9}

# ------------------------------------------------------------------ calendar
PROMOS = [("Summer sales", "2025-06-25", "2025-07-22", 1.25, 1.10, 0.92),
          ("Black Month", "2025-11-01", "2025-11-30", 1.90, 1.22, 0.86),
          ("Winter sales", "2026-01-07", "2026-02-03", 1.35, 1.12, 0.90),
          ("Summer sales", "2026-06-24", "2026-07-21", 1.25, 1.10, 0.92),
          ("Black Month", "2026-11-01", "2026-11-30", 1.90, 1.22, 0.86)]
BLACK_FRIDAY = [pd.Timestamp("2025-11-28"), pd.Timestamp("2026-11-27")]
WEEKDAY = np.array([1.05, 1.00, 0.98, 0.96, 0.92, 0.95, 1.12])  # Monday..Sunday
BASE_SESSIONS = 8_000

# ------------------------------------------------------------------ planted events (hidden truth)
EV_SAFARI = ("2026-03-10", "2026-03-18")    # 1. payment step -30% on Safari iOS only
EV_SLOW_PDP = ("2026-05-12", "2026-06-22")  # 2. mattress product pages +1.4 s LCP on mobile -> add-to-cart -22%
EV_MIX = ("2026-08-31", "2026-09-13")       # 4. cold paid-social push: x4 paid-social sessions, every segment stable
EV_DUP = ("2026-07-07", "2026-08-03")       # 5. purchase event sent twice for ~11% of orders
HIDDEN = [
    (1, "Mobile payment broken (Safari iOS)", *EV_SAFARI, "device=mobile/tablet, browser=Safari iOS",
     "payment step pass rate", "raise", "-30% payment-step pass rate after the split-payment widget release"),
    (2, "Slower mattress product page", *EV_SLOW_PDP, "device=mobile/tablet, category=Mattress",
     "add-to-cart rate", "raise", "LCP +1.4 s on mobile mattress PDPs, add-to-cart -22% (desktop unaffected)"),
    (3, "Delivery fees revealed at checkout (bulky items)", "2025-06-01", "2026-11-30",
     "category=Bed base & bed, Sofa", "shipping-step abandonment", "funnel finding",
     "abandonment at the shipping step is twice the other categories' (structural, not a break)"),
    (4, "False signal: traffic mix", *EV_MIX, "channel=Paid social", "conversion rate", "do not raise",
     "topline conversion falls while every segment is stable: more cold paid-social traffic"),
    (5, "Duplicate purchase events", *EV_DUP, "all", "analytics revenue vs shop", "raise",
     "purchase tag fired twice on ~11% of orders after a tag-manager change"),
    (6, "Sample ratio mismatch", "2026-04-06", "2026-05-03", "test B", "allocation", "invalidate test",
     "variant served by a redirect: 52/48 split instead of 50/50"),
    (7, "The winner that loses", "2026-08-31", "2026-10-25", "test D", "net revenue per visitor", "iterate",
     "conversion +6% but more 100-night returns: net revenue per visitor not significant"),
    (8, "Normal seasonality (Black Month)", "2026-11-01", "2026-11-30", "all", "sessions, conversion, AOV",
     "do not raise", "traffic x2, conversion up, basket down: expected from the promo calendar"),
]


def in_window(dates: pd.Series, window: tuple[str, str]) -> np.ndarray:
    return ((dates >= window[0]) & (dates <= window[1])).to_numpy()


def daily_factors() -> pd.DataFrame:
    d = pd.DataFrame({"date": DAYS})
    t = (d["date"] - START).dt.days.to_numpy()
    doy = d["date"].dt.dayofyear.to_numpy()
    traffic = (1.09 ** (t / 365)) * (1 + 0.08 * np.cos(2 * np.pi * (doy - 15) / 365)) * WEEKDAY[d["date"].dt.weekday]
    conv, aov, promo = np.ones(len(d)), np.ones(len(d)), np.array([""] * len(d), dtype=object)
    for name, a, b, ft, fc, fa in PROMOS:
        m = in_window(d["date"], (a, b))
        traffic[m] *= ft
        conv[m] *= fc
        aov[m] *= fa
        promo[m] = name
    for bf in BLACK_FRIDAY:  # Black Friday week peaks inside Black Month
        m = ((d["date"] >= bf - pd.Timedelta(days=3)) & (d["date"] <= bf + pd.Timedelta(days=3))).to_numpy()
        traffic[m] *= 1.35
        conv[m] *= 1.08
    return d.assign(traffic=traffic, conv=conv, aov=aov, promo=promo)


def segment_grid() -> pd.DataFrame:
    rows = []
    for dev, pdv in DEVICE.items():
        for br, pbr in BROWSER[dev].items():
            for ch, pch in CHANNEL.items():
                for vt in ("New", "Returning"):
                    pvt = RETURNING[ch] if vt == "Returning" else 1 - RETURNING[ch]
                    for cat, pcat in CATEGORY.items():
                        rows.append((dev, br, ch, vt, cat, pdv * pbr * pch * pvt * pcat))
    return pd.DataFrame(rows, columns=["device", "browser", "channel", "visitor_type", "entry_category", "share"])


def simulate_sessions() -> tuple[pd.DataFrame, pd.DataFrame]:
    days, seg = daily_factors(), segment_grid()
    g = days.merge(seg, how="cross")
    date = g["date"]
    lam = BASE_SESSIONS * g["traffic"] * g["share"]
    mix = in_window(date, EV_MIX) & (g["channel"] == "Paid social").to_numpy()
    lam = lam * np.where(mix, 4.0, 1.0)
    n = len(g)
    s = rng.poisson(lam.to_numpy())

    atc_f = (g["device"].map(F_ATC["device"]) * g["browser"].map(F_ATC["browser"]) * g["channel"].map(F_ATC["channel"])
             * g["visitor_type"].map(F_ATC["visitor"]) * g["entry_category"].map(F_ATC["category"])).to_numpy()
    chk_f = (g["device"].map(F_CHK["device"]) * g["visitor_type"].map(F_CHK["visitor"])).to_numpy()
    mobile_like = g["device"].isin(["mobile", "tablet"]).to_numpy()
    slow = in_window(date, EV_SLOW_PDP) & mobile_like & (g["entry_category"] == "Mattress").to_numpy()
    atc_f = atc_f * np.where(slow, 0.78, 1.0)
    conv = g["conv"].to_numpy()
    p_ship = np.where(g["entry_category"].isin(BULKY), P["shipping_given_checkout"] * SHIPPING_BULKY,
                      P["shipping_given_checkout"])
    safari = in_window(date, EV_SAFARI) & (g["browser"] == "Safari iOS").to_numpy()
    p_pay = P["payment_given_shipping"] * np.where(safari, 0.70, 1.0)

    def b(k, p):
        return rng.binomial(k, np.clip(p, 0, 0.98))

    cat_views = b(s, P["category_view"])
    pdp = b(s, P["pdp_view"])
    atc = b(pdp, P["atc_given_pdp"] * atc_f * np.sqrt(conv))
    cart = b(atc, P["cart_given_atc"])
    chk = b(atc, P["checkout_given_atc"] * chk_f * np.sqrt(conv))
    ship = b(chk, p_ship)
    pay = b(ship, p_pay)
    orders = b(pay, P["order_given_payment"])
    users = np.maximum(np.minimum(s, np.round(s / g["visitor_type"].map(SESSIONS_PER_USER).to_numpy())), (s > 0) * 1)

    out = g[["date", "device", "browser", "channel", "visitor_type", "entry_category"]].copy()
    out = out.assign(sessions=s, users=users.astype(int), category_views=cat_views, product_views=pdp,
                     add_to_cart=atc, cart_views=cart, checkout_starts=chk, shipping_completed=ship,
                     payment_completed=pay, orders=orders)
    out = out[out["sessions"] > 0].reset_index(drop=True)

    # ---- orders: one row per order, basket, split payment, 100-night return
    idx = np.repeat(out.index.to_numpy(), out["orders"].to_numpy())
    o = out.loc[idx, ["date", "device", "browser", "channel", "visitor_type", "entry_category"]].reset_index(drop=True)
    o = o.rename(columns={"entry_category": "category"})
    aov_f = o["date"].map(days.set_index("date")["aov"]).to_numpy()
    mean = o["category"].map(AOV).to_numpy() * aov_f
    sigma = 0.35
    basket = np.round(rng.lognormal(np.log(mean) - sigma ** 2 / 2, sigma), 2)
    p_split = np.where(basket >= 400, 0.38, np.where(basket >= 50, 0.08, 0.0))
    split = rng.random(len(o)) < p_split
    returned = rng.random(len(o)) < o["category"].map(RETURN_RATE).to_numpy()
    lag = rng.integers(8, 104, len(o))  # delivery + up to 100 nights
    ret_date = o["date"] + pd.to_timedelta(lag, unit="D")
    observed = returned & (ret_date <= AS_OF).to_numpy()
    o = o.assign(order_id=[f"O{i:07d}" for i in range(1, len(o) + 1)], basket_eur=basket, split_payment=split,
                 returned=observed, return_date=ret_date.where(observed))
    o = o[["order_id", "date", "category", "device", "browser", "channel", "visitor_type", "basket_eur",
           "split_payment", "returned", "return_date"]]
    rev = o.groupby(idx)["basket_eur"].sum() if len(o) else pd.Series(dtype=float)
    out["revenue_eur"] = rev.reindex(out.index).fillna(0).round(2).to_numpy()
    return out, o


def simulate_reconciliation(orders: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(4343)
    day = orders.groupby("date").agg(shop_orders=("order_id", "size"), shop_revenue_eur=("basket_eur", "sum"))
    day = day.reindex(DAYS, fill_value=0)
    captured = rng.binomial(day["shop_orders"].to_numpy(), 0.965)  # consent / ad-blockers: ~3.5% never tracked
    dup_rate = np.where(in_window(pd.Series(DAYS), EV_DUP), 0.11, 0.004)
    dups = rng.binomial(captured, dup_rate)
    avg = (day["shop_revenue_eur"] / day["shop_orders"].replace(0, np.nan)).fillna(0).to_numpy()
    noise = rng.normal(1, 0.01, len(day))
    return pd.DataFrame({"date": DAYS, "shop_orders": day["shop_orders"].to_numpy(),
                         "shop_revenue_eur": day["shop_revenue_eur"].round(2).to_numpy(),
                         "analytics_purchase_events": captured + dups, "analytics_transactions": captured,
                         "analytics_revenue_eur": np.round((captured + dups) * avg * noise, 2)})


def simulate_page_speed() -> pd.DataFrame:
    rng = np.random.default_rng(4444)
    base = {"Homepage": (2.3, 1.4), "Category page": (2.5, 1.5), "Product page - mattress": (2.7, 1.6),
            "Product page - other": (2.6, 1.6), "Cart": (1.9, 1.2)}
    rows = []
    slow = in_window(pd.Series(DAYS), EV_SLOW_PDP)
    for page, (mob, desk) in base.items():
        m = mob + rng.normal(0, 0.08, len(DAYS)) + np.where(slow & (page == "Product page - mattress"), 1.4, 0)
        d = desk + rng.normal(0, 0.05, len(DAYS))
        rows.append(pd.DataFrame({"date": DAYS, "page_type": page, "lcp_mobile_p50_s": m.round(2),
                                  "lcp_desktop_p50_s": d.round(2)}))
    return pd.concat(rows, ignore_index=True)


# A/B tests: visitor-level (testing-tool export). Effects are relative to control.
TESTS = [  # id, name, start, end, population, visitors/day, base conv, base atc, effects, srm
    ("A", "Sticky add-to-cart button on mobile product pages", "2026-02-09", "2026-03-08",
     "mobile visitors of product pages", 3100, 0.018, 0.090,
     {"atc": 1.075, "conv": 1.03, "ret": 1.0}, 0.50),
    ("B", "'100-night trial' reassurance next to the add-to-cart button", "2026-04-06", "2026-05-03",
     "visitors of product pages", 4600, 0.020, 0.085, {"atc": 1.03, "conv": 1.02, "ret": 1.0}, 0.48),
    ("C", "Delivery fee shown on bulky-item product pages", "2026-06-22", "2026-08-09",
     "visitors of bed base, bed and sofa product pages", 1800, 0.016, 0.080,
     {"atc": 0.96, "conv": 1.20, "ret": 1.0}, 0.50),
    ("D", "Mattress comparator", "2026-08-31", "2026-10-25", "all visitors", 6000, 0.016, 0.070,
     {"atc": 1.06, "conv": 1.065, "ret": 1.50}, 0.50),
]
TEST_AOV, TEST_RET = 640, 0.075


def simulate_experiments() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(4242)  # own stream: tuning the store does not change the tests
    daily, orders = [], []
    for tid, name, a, b, pop, vpd, conv, atc, eff, share_b in TESTS:
        dates = pd.date_range(a, b, freq="D")
        for date in dates:
            n = rng.poisson(vpd * WEEKDAY[date.weekday()])
            n_b = rng.binomial(n, share_b)
            for variant, nv in (("control", n - n_b), ("variant", n_b)):
                f = eff if variant == "variant" else {"atc": 1, "conv": 1, "ret": 1}
                k_atc = rng.binomial(nv, atc * f["atc"])
                k = rng.binomial(nv, conv * f["conv"])
                val = np.round(rng.lognormal(np.log(TEST_AOV) - 0.5 ** 2 / 2, 0.5, k), 2)
                ret = rng.random(k) < TEST_RET * f["ret"]
                daily.append((tid, name, pop, date, variant, nv, k_atc, k, val.sum().round(2), int(ret.sum()),
                              val[ret].sum().round(2)))
                orders += [(tid, variant, date, v, bool(r)) for v, r in zip(val, ret)]
    exp = pd.DataFrame(daily, columns=["test_id", "test_name", "population", "date", "variant", "visitors",
                                       "add_to_cart_visitors", "orders", "revenue_eur", "returned_orders",
                                       "returned_revenue_eur"])
    eo = pd.DataFrame(orders, columns=["test_id", "variant", "date", "basket_eur", "returned"])
    return exp, eo


RELEASES = [
    ("2025-06-10", "Homepage", "New summer-sales hero banner"),
    ("2025-07-01", "Product page", "Size selector redesigned (buttons instead of dropdown)"),
    ("2025-08-19", "Site-wide", "Theme update (Shopify theme minor version)"),
    ("2025-09-09", "Category page", "Filters moved to a side drawer on mobile"),
    ("2025-10-14", "Checkout", "New delivery-slot picker"),
    ("2025-10-28", "Homepage", "Black Month landing blocks"),
    ("2025-12-02", "Site-wide", "Black Month content removed"),
    ("2026-01-06", "Homepage", "Winter-sales banners"),
    ("2026-02-09", "Product page", "A/B test A launched (sticky add-to-cart, mobile)"),
    ("2026-03-09", "Homepage", "New hero image and headline"),
    ("2026-03-10", "Checkout - payment", "Split-payment widget upgraded to a new version (new iframe)"),
    ("2026-03-12", "Blog", "New article template"),
    ("2026-03-19", "Checkout - payment", "Hotfix: split-payment widget rendering on WebKit browsers"),
    ("2026-04-06", "Product page", "A/B test B launched (reassurance block; variant served by a redirect)"),
    ("2026-04-21", "Footer", "Store-locator links updated"),
    ("2026-05-11", "Site-wide", "Cookie banner wording updated"),
    ("2026-05-12", "Product page - mattress", "New full-width image carousel with high-resolution images"),
    ("2026-05-26", "Category page", "Kids range collection page restyled"),
    ("2026-06-23", "Product page - mattress", "Carousel images resized and lazy-loaded"),
    ("2026-06-22", "Product page - bulky", "A/B test C launched (delivery fee shown on product page)"),
    ("2026-07-06", "Blog", "Category pages for the blog"),
    ("2026-07-07", "Tracking", "Purchase tag migrated to a new tag-manager container"),
    ("2026-08-04", "Tracking", "Old purchase trigger removed from the previous container"),
    ("2026-08-31", "Site-wide", "A/B test D launched (mattress comparator)"),
    ("2026-09-15", "Account", "Order-tracking page redesigned"),
    ("2026-10-13", "Homepage", "Reviews widget moved higher on mobile"),
    ("2026-10-27", "Homepage", "Black Month landing blocks"),
]
MARKETING = [("2026-08-31", "2026-09-13", "Paid social", "Awareness campaign, broad audiences (prospecting)")]


def main() -> None:
    SIM.mkdir(parents=True, exist_ok=True)
    sessions, orders = simulate_sessions()
    recon = simulate_reconciliation(orders)
    speed = simulate_page_speed()
    exp, exp_orders = simulate_experiments()
    releases = pd.DataFrame(RELEASES, columns=["release_date", "area", "description"])
    releases["release_date"] = pd.to_datetime(releases["release_date"])
    promo = pd.DataFrame([(n, pd.Timestamp(a), pd.Timestamp(b)) for n, a, b, *_ in PROMOS],
                         columns=["promo", "start_date", "end_date"])
    mkt = pd.DataFrame(MARKETING, columns=["start_date", "end_date", "channel", "note"])
    for name, df in {"sessions_daily": sessions, "orders": orders, "ga4_vs_shop_daily": recon,
                     "page_speed_daily": speed, "experiments": exp, "experiment_orders": exp_orders,
                     "releases": releases, "promo_calendar": promo, "marketing_calendar": mkt}.items():
        df.to_parquet(SIM / f"{name}.parquet", index=False)
    pd.DataFrame(HIDDEN, columns=["event_id", "event", "start_date", "end_date", "segment", "kpi",
                                  "expected_handling", "description"]).to_csv(ROOT / "data" / "_hidden_truth.csv",
                                                                             index=False)
    print(f"sessions_daily: {len(sessions):,} rows, {sessions['sessions'].sum():,} sessions, "
          f"{sessions['orders'].sum():,} orders, conversion {sessions['orders'].sum() / sessions['sessions'].sum():.3%}, "
          f"revenue EUR {sessions['revenue_eur'].sum() / 1e6:.1f} M")
    print(f"orders: {len(orders):,} rows; return rate {orders['returned'].mean():.1%}; experiments: {len(exp):,} rows")


if __name__ == "__main__":
    main()
