"""Company facts from the French company register open API (PUBLIC DATA, Etalab open licence).

Keeps only legal facts (no officer name is written anywhere):
SIREN, creation date, activity code, headcount band, category, head-office postcode, published accounts.

    python src/collect_registry.py   -> data/processed/tediber_registry.csv
"""
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
API = "https://recherche-entreprises.api.gouv.fr/search"
BANDS = {"21": "50 to 99 employees"}

if __name__ == "__main__":
    r = requests.get(API, params={"q": "tediber"}, headers={"User-Agent": "cro-case-study/1.0"}, timeout=30).json()
    c = next(x for x in r["results"] if x["siren"] == "813089638")
    rows = [("SIREN", c["siren"]), ("Name", c["nom_raison_sociale"] or c["nom_complet"]),
            ("Created", c["date_creation"]), ("Activity code (NAF)", f"{c['activite_principale']} - mail-order sale of specialised goods"),
            ("Headcount band", f"{BANDS.get(c['tranche_effectif_salarie'], c['tranche_effectif_salarie'])} ({c['annee_tranche_effectif_salarie']})"),
            ("Company category", c["categorie_entreprise"]), ("Head office", f"{c['siege']['code_postal']} {c['siege']['libelle_commune']}")]
    for year, f in sorted((c.get("finances") or {}).items()):
        rows += [(f"Revenue {year} (EUR)", f["ca"]), (f"Net income {year} (EUR)", f["resultat_net"])]
    years = sorted((c.get("finances") or {}))
    rows.append(("Latest accounts in the API", years[-1] if years else "none"))
    pd.DataFrame(rows, columns=["field", "value"]).assign(source="recherche-entreprises.api.gouv.fr",
                                                          retrieved_on=date.today().isoformat()).to_csv(
        ROOT / "data" / "processed" / "tediber_registry.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))
