"""Lab page-speed measures of Tediber's public pages with Lighthouse (PUBLIC DATA, measured by us).

6 public pages (homepage, 2 category pages, 3 product pages) x 2 form factors (mobile, desktop) x 3 runs,
60 s apart, medians kept. Cart, checkout, account and search pages are never loaded (robots.txt).
These are LAB data (one simulated device and network), not real-user data (CrUX); see src/fetch_crux.py.
Lighthouse needs Node.js; Edge is used as the Chromium browser (CHROME_PATH).

    python src/run_lighthouse.py            -> raw JSON in data/raw/lighthouse/ (not committed: it holds local paths)
    python src/run_lighthouse.py --parse    -> data/processed/lighthouse_summary.csv (medians, no local path)
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw" / "lighthouse", ROOT / "data" / "processed"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PAGES = {
    "home": ("Homepage", "https://www.tediber.com/"),
    "cat_mattress": ("Category page", "https://www.tediber.com/collections/matelas"),
    "cat_bedbase": ("Category page", "https://www.tediber.com/collections/sommier"),
    "pdp_mattress": ("Product page", "https://www.tediber.com/products/matelas-hybride"),
    "pdp_bedbase": ("Product page", "https://www.tediber.com/products/sommier"),
    "pdp_duvet": ("Product page", "https://www.tediber.com/products/couette"),
}
RUNS, PAUSE_S = 3, 60
METRICS = {"largest-contentful-paint": "lcp_s", "cumulative-layout-shift": "cls",
           "total-blocking-time": "tbt_ms", "first-contentful-paint": "fcp_s", "speed-index": "speed_index_s",
           "total-byte-weight": "page_weight_kb"}


def run() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CHROME_PATH": EDGE}
    for i in range(1, RUNS + 1):
        for key, (_, url) in PAGES.items():
            for ff in ("mobile", "desktop"):
                out = RAW / f"{key}_{ff}_{i}.json"
                if out.exists():
                    continue
                cmd = ["npx", "-y", "lighthouse@12.8.2", url, "--output=json", f"--output-path={out}",
                       "--only-categories=performance", "--quiet",
                       "--chrome-flags=--headless=new --no-first-run --disable-extensions"]
                if ff == "desktop":
                    cmd.append("--preset=desktop")
                print(f"run {i} {key} {ff}", flush=True)
                subprocess.run(" ".join(f'"{c}"' if " " in c else c for c in cmd), shell=True, env=env,
                               timeout=300, check=False)
                time.sleep(PAUSE_S)


def parse() -> pd.DataFrame:
    rows = []
    for f in sorted(RAW.glob("*.json")):
        key, ff, i = f.stem.rsplit("_", 2)
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("runtimeError") or "audits" not in d:
            continue
        a = d["audits"]
        row = {"page": key, "page_type": PAGES[key][0], "url": PAGES[key][1], "form_factor": ff, "run": int(i),
               "performance_score": round(100 * (d["categories"]["performance"]["score"] or 0))}
        tp = a.get("third-party-summary", {}).get("details", {}).get("items", [])
        row["third_party_entities"] = len(tp)
        row["third_party_kb"] = sum(i.get("transferSize", 0) for i in tp) / 1024
        for audit, col in METRICS.items():
            v = a.get(audit, {}).get("numericValue")
            if v is None:
                continue
            row[col] = v / 1000 if col.endswith("_s") else v / 1024 if col.endswith("_kb") else v
        rows.append(row)
    runs = pd.DataFrame(rows)
    num = ["performance_score", *METRICS.values(), "third_party_entities", "third_party_kb"]
    med = (runs.groupby(["page", "page_type", "url", "form_factor"])[num].median().round(3)
           .join(runs.groupby(["page", "page_type", "url", "form_factor"]).size().rename("runs")).reset_index())
    med["measured_on"] = "2026-11-17"
    med["source"] = "Lighthouse 12.8.2 lab run (median), Edge headless"
    med.to_csv(OUT / "lighthouse_summary.csv", index=False)
    return med


if __name__ == "__main__":
    if "--parse" not in sys.argv:
        run()
    print(parse().to_string(index=False))
