"""Market context from Eurostat (PUBLIC DATA, open API, re-use allowed with attribution).

- isoc_ec_ib20, I_BUY3: individuals who bought online in the last 3 months (% of individuals)
- isoc_ec_ibgs, I_BFURN1: individuals who bought furniture, home accessories or gardening products online
  in the last 3 months (% of individuals)
France vs EU-27 (EU27_2020), 2020-2025.

    python src/collect_market.py   -> data/processed/market_eurostat.csv
"""
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{ds}"
SERIES = [("isoc_ec_ib20", "I_BUY3", "Bought online, last 3 months"),
          ("isoc_ec_ibgs", "I_BFURN1", "Bought furniture / home goods online, last 3 months")]


def fetch(ds: str, indic: str, geo: str) -> pd.DataFrame:
    params = {"format": "JSON", "lang": "EN", "geo": geo, "unit": "PC_IND", "ind_type": "IND_TOTAL",
              "indic_is": indic}
    d = requests.get(API.format(ds=ds), params=params, headers={"User-Agent": "cro-case-study/1.0"},
                     timeout=60).json()
    years = d["dimension"]["time"]["category"]["index"]  # {"2020": 0, ...}
    return pd.DataFrame([{"dataset": ds, "indicator": indic, "geo": geo, "year": int(y),
                          "pct_individuals": d["value"].get(str(i))} for y, i in years.items()])


if __name__ == "__main__":
    frames = [fetch(ds, ind, geo).assign(label=label) for ds, ind, label in SERIES for geo in ("FR", "EU27_2020")]
    out = pd.concat(frames).dropna(subset=["pct_individuals"]).assign(retrieved_on=date.today().isoformat())
    out.to_csv(ROOT / "data" / "processed" / "market_eurostat.csv", index=False)
    print(out.pivot_table(index=["indicator", "geo"], columns="year", values="pct_individuals"))
