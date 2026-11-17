"""Run the SQL files with DuckDB and export the results to data/processed/.

Views created before running:
- ga4_events  = real GA4 sample (data/raw/ga4/ga4_funnel_events.parquet, from src/extract_ga4.py), if present;
- every simulated table data/sim/<name>.parquet becomes a view <name>.
Order: sql/ga4/*.sql (skipped if the GA4 extract is absent: its aggregates are already in data/processed),
then sql/*.sql. A statement preceded by '-- output: <name>' is exported to data/processed/<name>.csv.

    python src/run_sql.py            (all files)
    python src/run_sql.py 01 03      (only files whose name starts with these prefixes)
"""
import re
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIM, OUT, SQL = ROOT / "data" / "sim", ROOT / "data" / "processed", ROOT / "sql"
GA4 = ROOT / "data" / "raw" / "ga4" / "ga4_funnel_events.parquet"


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    if GA4.exists():
        con.execute(f"CREATE OR REPLACE VIEW ga4_events AS SELECT * FROM read_parquet('{GA4.as_posix()}')")
    for f in sorted(SIM.glob("*.parquet")):
        con.execute(f"CREATE OR REPLACE VIEW {f.stem} AS SELECT * FROM read_parquet('{f.as_posix()}')")
    return con


def run_file(con: duckdb.DuckDBPyConnection, sql_file: Path) -> None:
    t0 = time.time()
    for statement in re.split(r";\s*$", sql_file.read_text(encoding="utf-8"), flags=re.MULTILINE):
        if not re.search(r"^\s*[A-Za-z(]", statement, flags=re.MULTILINE):
            continue  # comments only
        match = re.search(r"--\s*output:\s*(\w+)", statement)
        if match:
            df = con.execute(statement).df()
            for c in df.select_dtypes("float").columns:  # 8 significant digits -> reproducible CSVs
                df[c] = df[c].map(lambda v: float(f"{v:.8g}") if pd.notna(v) else v)
            df.to_csv(OUT / f"{match.group(1)}.csv", index=False)
            print(f"  {sql_file.name:28s} -> {match.group(1)}.csv ({len(df):,} rows)")
        else:
            con.execute(statement)
    print(f"{sql_file.relative_to(ROOT).as_posix()} done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    con = connect()
    prefixes = tuple(sys.argv[1:])
    files = sorted((SQL / "ga4").glob("*.sql")) + sorted(SQL.glob("*.sql"))
    for f in files:
        if prefixes and not f.name.startswith(prefixes):
            continue
        if f.parent.name == "ga4" and not GA4.exists():
            print(f"skip {f.name}: run src/extract_ga4.py first (its outputs are already in data/processed)")
            continue
        run_file(con, f)
