"""Extract the real GA4 e-commerce events (PUBLIC DATA, another store) used for the real-funnel analysis.

Source: Google's public BigQuery dataset `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
(Google Merchandise Store, 1 Nov 2020 - 31 Jan 2021, obfuscated). Without a Google Cloud account we read
a flattened CSV export of that same table published on Hugging Face (gizdevans/ga4-bq-flattened-data,
MIT licence, one row per event, event_params unnested). DuckDB streams the file over HTTPS and keeps only
the e-commerce funnel events and the columns we need, so the ~1.8 GB file is never stored.
With BigQuery access, the queries in sql/ga4/ run on the official tables.

    python src/extract_ga4.py
Output: data/raw/ga4/ga4_funnel_events.parquet (NOT committed: it holds visitor pseudo-ids).
Only aggregates are published (data/processed/ga4_*.csv, built by src/run_sql.py).
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
URL = "https://huggingface.co/datasets/gizdevans/ga4-bq-flattened-data/resolve/main/full_flatten_data.csv"
OUT = ROOT / "data" / "raw" / "ga4" / "ga4_funnel_events.parquet"
EVENTS = ("session_start", "page_view", "view_item_list", "select_item", "view_item", "add_to_cart",
          "view_cart", "begin_checkout", "add_shipping_info", "add_payment_info", "purchase")

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    events_sql = ", ".join(f"'{e}'" for e in EVENTS)
    con.execute(f"""
    COPY (
      SELECT event_date, event_name, CAST(event_timestamp AS BIGINT) AS event_timestamp,
             user_pseudo_id, ga_session_id, TRY_CAST(ga_session_number AS INTEGER) AS ga_session_number,
             page_location, page_title, device_category, browser, device_os, country,
             traffic_source, traffic_medium,
             TRY_CAST(engagement_time_msec AS BIGINT) AS engagement_time_msec,
             TRY_CAST(percent_scrolled AS INTEGER) AS percent_scrolled,
             TRY_CAST(ecom_revenue_usd AS DOUBLE) AS ecom_revenue_usd, ecom_transaction_id
      FROM read_csv('{URL}', header = true, all_varchar = true, parallel = false)
      WHERE event_name IN ({events_sql})
    ) TO '{OUT.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    for name, n in con.execute(f"SELECT event_name, count(*) n FROM read_parquet('{OUT.as_posix()}') GROUP BY 1 ORDER BY 2 DESC").fetchall():
        print(f"{name:20s} {n:>10,}")
