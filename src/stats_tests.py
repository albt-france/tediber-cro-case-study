"""Statistics used to plan and read A/B tests (shared by the notebook, the Excel checks and the dashboard).

- sample_size_per_arm: visitors needed per variant to detect a relative lift (two-sided test on proportions)
- two_proportion_test: z test, p-value and confidence interval of the difference and of the relative lift
- srm_check: chi-square test of the observed split against the planned split (Sample Ratio Mismatch)
- bootstrap_rpv: bootstrap confidence interval of the relative lift in (net) revenue per visitor
- peeking_false_positive_rate: how often an A/A test "wins" if you stop at the first p < 0.05
- read_test: the whole read-out of one test from data/processed/experiment_summary.csv + experiment_orders
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats


def sample_size_per_arm(p_base: float, mde_rel: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Visitors per arm to detect p_base -> p_base x (1 + mde_rel), two-sided, unpooled variances."""
    p1, p2 = p_base, p_base * (1 + mde_rel)
    z_a, z_b = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    return math.ceil((z_a + z_b) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p2 - p1) ** 2)


def mde_for_sample(p_base: float, n_per_arm: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """Smallest relative lift detectable with n visitors per arm (approximation with the base variance)."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return z * math.sqrt(2 * p_base * (1 - p_base) / n_per_arm) / p_base


def two_proportion_test(x_a: int, n_a: int, x_b: int, n_b: int, alpha: float = 0.05) -> dict:
    """B vs A. z test with pooled variance; CI on the difference with unpooled variance."""
    p_a, p_b = x_a / n_a, x_b / n_b
    p = (x_a + x_b) / (n_a + n_b)
    z = (p_b - p_a) / math.sqrt(p * (1 - p) * (1 / n_a + 1 / n_b))
    se = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    q = stats.norm.ppf(1 - alpha / 2)
    diff = p_b - p_a
    return {"rate_a": p_a, "rate_b": p_b, "diff": diff, "lift": p_b / p_a - 1, "z": z,
            "p_value": 2 * stats.norm.sf(abs(z)), "ci_diff_low": diff - q * se, "ci_diff_high": diff + q * se,
            "ci_lift_low": (diff - q * se) / p_a, "ci_lift_high": (diff + q * se) / p_a}


def srm_check(n_a: int, n_b: int, planned_share_b: float = 0.5) -> dict:
    """Chi-square goodness of fit of the observed split. p < 0.001 -> allocation broken, do not read the test."""
    n = n_a + n_b
    exp_a, exp_b = n * (1 - planned_share_b), n * planned_share_b
    chi2 = (n_a - exp_a) ** 2 / exp_a + (n_b - exp_b) ** 2 / exp_b
    p = stats.chi2.sf(chi2, df=1)
    return {"share_b": n_b / n, "chi2": chi2, "p_value": p, "srm": p < 0.001}


def bootstrap_rpv(values_a: np.ndarray, n_a: int, values_b: np.ndarray, n_b: int, n_boot: int = 4000,
                  seed: int = 7) -> dict:
    """Bootstrap CI of the relative lift in revenue per visitor.
    values_* are the per-order (net) values; the n_* - len(values_*) other visitors are zeros. Resampling
    visitors with replacement = drawing the number of buyers (binomial), then resampling their values."""
    rng = np.random.default_rng(seed)
    va, vb = np.asarray(values_a, float), np.asarray(values_b, float)
    ka, kb = rng.binomial(n_a, len(va) / n_a, n_boot), rng.binomial(n_b, len(vb) / n_b, n_boot)
    rpv_a = np.array([rng.choice(va, k).sum() / n_a for k in ka])
    rpv_b = np.array([rng.choice(vb, k).sum() / n_b for k in kb])
    lift = rpv_b / rpv_a - 1
    point = (vb.sum() / n_b) / (va.sum() / n_a) - 1
    return {"rpv_a": va.sum() / n_a, "rpv_b": vb.sum() / n_b, "lift": point,
            "ci_low": float(np.percentile(lift, 2.5)), "ci_high": float(np.percentile(lift, 97.5)),
            "p_value": float(min(1.0, 2 * min((lift <= 0).mean(), (lift >= 0).mean())))}


def peeking_false_positive_rate(p: float = 0.02, n_per_day: int = 1500, days: int = 28, n_sims: int = 2000,
                                seed: int = 11) -> dict:
    """A/A simulation: no real difference. Compare 'look once at the end' with 'look every day, stop at the
    first p < 0.05'. The second inflates the false-positive rate well above 5 %."""
    rng = np.random.default_rng(seed)
    xa = rng.binomial(n_per_day, p, (n_sims, days)).cumsum(1)
    xb = rng.binomial(n_per_day, p, (n_sims, days)).cumsum(1)
    n = n_per_day * np.arange(1, days + 1)
    pool = (xa + xb) / (2 * n)
    z = (xb / n - xa / n) / np.sqrt(pool * (1 - pool) * 2 / n)
    sig = np.abs(z) > stats.norm.ppf(0.975)
    return {"fixed_horizon": float(sig[:, -1].mean()), "daily_peeking": float(sig.any(1).mean()),
            "by_day": [float(sig[:, : d + 1].any(1).mean()) for d in range(days)]}


def read_test(summary: pd.DataFrame, orders: pd.DataFrame, test_id: str) -> dict:
    """Full read-out of one test: SRM first, then conversion, add-to-cart, gross and net revenue per visitor."""
    s = summary[summary["test_id"] == test_id].set_index("variant")
    a, b = s.loc["control"], s.loc["variant"]
    out = {"test_id": test_id, "test_name": a["test_name"], "visitors_a": int(a["visitors"]),
           "visitors_b": int(b["visitors"])}
    out["srm"] = srm_check(int(a["visitors"]), int(b["visitors"]))
    out["conversion"] = two_proportion_test(int(a["orders"]), int(a["visitors"]), int(b["orders"]), int(b["visitors"]))
    out["add_to_cart"] = two_proportion_test(int(a["atc_visitors"]), int(a["visitors"]),
                                             int(b["atc_visitors"]), int(b["visitors"]))
    o = orders[orders["test_id"] == test_id]
    ga, gb = o[o["variant"] == "control"], o[o["variant"] == "variant"]
    out["rpv_gross"] = bootstrap_rpv(ga["basket_eur"].to_numpy(), int(a["visitors"]),
                                     gb["basket_eur"].to_numpy(), int(b["visitors"]))
    net = lambda g: np.where(g["returned"], 0.0, g["basket_eur"])  # noqa: E731 - a returned order is worth 0
    out["rpv_net"] = bootstrap_rpv(net(ga), int(a["visitors"]), net(gb), int(b["visitors"]))
    out["return_rate_a"], out["return_rate_b"] = ga["returned"].mean(), gb["returned"].mean()
    out["returns"] = two_proportion_test(int(ga["returned"].sum()), len(ga), int(gb["returned"].sum()), len(gb))
    out["decision"] = decide(out)
    return out


def decide(r: dict) -> str:
    """Ship / iterate / drop rule written before the tests (docs/ab_tests/README.md).
    - invalid allocation (SRM) -> 'invalid: fix and relaunch' (nothing is read)
    - primary metric up (p < 0.05) and no guardrail breached -> ship
    - primary metric up but a guardrail breached (100-night return rate up with p < 0.05, or net revenue
      per visitor interval entirely below 0) -> iterate: keep the idea, fix what hurts, test again
    - primary metric not significantly up -> drop"""
    if r["srm"]["srm"]:
        return "invalid: fix and relaunch"
    primary = r["add_to_cart"] if r["test_id"] == "A" else r["conversion"]
    up = primary["p_value"] < 0.05 and primary["lift"] > 0
    breached = (r["returns"]["p_value"] < 0.05 and r["returns"]["lift"] > 0) or r["rpv_net"]["ci_high"] < 0
    if up and not breached:
        return "ship"
    if up:
        return "iterate"
    return "drop"
