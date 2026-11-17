-- =====================================================================================================
-- Real GA4 e-commerce funnel (PUBLIC DATA - Google Merchandise Store, NOT Tediber), 1 Nov 2020 - 31 Jan 2021
-- Source view: ga4_events = data/raw/ga4/ga4_funnel_events.parquet (src/extract_ga4.py)
-- Written for DuckDB; the same logic runs on BigQuery (events_* tables) by replacing the source view
-- and unnesting event_params for page_location / ga_session_id / ga_session_number.
-- A session = user_pseudo_id + ga_session_id (ga_session_id alone is not unique across users).
-- =====================================================================================================

-- 1. One row per session with its segments and the funnel steps it reached (open funnel: any order)
CREATE OR REPLACE TABLE ga4_sessions AS
WITH ev AS (
  SELECT *, user_pseudo_id || '-' || ga_session_id AS session_key
  FROM ga4_events
  WHERE ga_session_id IS NOT NULL
),
product_urls AS (                       -- a URL is a product page if a view_item event happened on it
  SELECT DISTINCT split_part(page_location, '?', 1) AS url FROM ev WHERE event_name = 'view_item'
),
first_page AS (                         -- landing page = first page_view of the session
  SELECT session_key, arg_min(split_part(page_location, '?', 1), event_timestamp) AS landing_url
  FROM ev WHERE event_name = 'page_view' GROUP BY 1
)
SELECT
  e.session_key,
  min(e.event_date)                                             AS event_date,
  any_value(e.device_category)                                  AS device,
  CASE WHEN any_value(e.browser) = 'Safari' AND any_value(e.device_os) = 'iOS' THEN 'Safari iOS'
       WHEN any_value(e.browser) = 'Chrome' THEN 'Chrome' ELSE 'Other' END AS browser_group,
  -- traffic_source / traffic_medium in the export describe the USER's first acquisition, not the session
  CASE any_value(e.traffic_medium)
       WHEN 'organic' THEN 'Organic search' WHEN 'cpc' THEN 'Paid search'
       WHEN '(none)' THEN 'Direct' WHEN 'referral' THEN 'Referral'
       ELSE 'Other / not available' END                         AS first_user_channel,
  CASE WHEN min(e.ga_session_number) = 1 THEN 'New' ELSE 'Returning' END AS visitor_type,
  CASE WHEN fp.landing_url IS NULL THEN 'No page_view'
       WHEN regexp_matches(fp.landing_url, '^https?://[^/]+/?$') THEN 'Home'
       WHEN fp.landing_url IN (SELECT url FROM product_urls) THEN 'Product page'
       WHEN regexp_matches(lower(fp.landing_url), '/google\+redesign|/google redesign') THEN 'Category page'
       WHEN regexp_matches(fp.landing_url, 'basket|signin|yourinfo|payment|revieworder') THEN 'Cart / checkout'
       ELSE 'Other page' END                                    AS landing_type,
  max(e.event_name = 'session_start')::INT                      AS has_session_start,
  max(e.event_name = 'view_item')::INT                          AS s1_view_item,
  max(e.event_name = 'add_to_cart')::INT                        AS s2_add_to_cart,
  max(e.event_name = 'begin_checkout')::INT                     AS s3_begin_checkout,
  max(e.event_name = 'add_shipping_info')::INT                  AS s4_shipping,
  max(e.event_name = 'add_payment_info')::INT                   AS s5_payment,
  max(e.event_name = 'purchase')::INT                           AS s6_purchase,
  sum(CASE WHEN e.event_name = 'purchase' THEN e.ecom_revenue_usd END) AS revenue_usd_raw
FROM ev e LEFT JOIN first_page fp USING (session_key)
GROUP BY e.session_key, fp.landing_url;

-- 2. Funnel by segment (long format: one row per segment value). Rates are step-to-step pass rates.
-- output: ga4_funnel_segments
WITH seg AS (
  SELECT 'All' AS dimension, 'All sessions' AS segment, * FROM ga4_sessions
  UNION ALL SELECT 'Device', device, * FROM ga4_sessions
  UNION ALL SELECT 'Browser', browser_group, * FROM ga4_sessions
  UNION ALL SELECT 'First-user channel', first_user_channel, * FROM ga4_sessions
  UNION ALL SELECT 'Visitor type', visitor_type, * FROM ga4_sessions
  UNION ALL SELECT 'Landing page', landing_type, * FROM ga4_sessions
)
SELECT dimension, segment,
       count(*)               AS sessions,
       sum(s1_view_item)      AS view_item,
       sum(s2_add_to_cart)    AS add_to_cart,
       sum(s3_begin_checkout) AS begin_checkout,
       sum(s4_shipping)       AS add_shipping_info,
       sum(s5_payment)        AS add_payment_info,
       sum(s6_purchase)       AS purchase,
       round(sum(s6_purchase) / count(*), 5)                                AS conversion_rate,
       round(sum(s2_add_to_cart) / count(*), 5)                             AS add_to_cart_rate,
       round(1 - sum(s6_purchase) / nullif(sum(s3_begin_checkout), 0), 5)   AS checkout_abandonment
FROM seg
GROUP BY ALL
HAVING count(*) >= 500
ORDER BY dimension, sessions DESC;

-- 3. Weekly funnel (real data) - the shape of a weekly report on a real export
-- output: ga4_weekly
SELECT date_trunc('week', strptime(event_date, '%Y%m%d'))::DATE AS week_start,
       device,
       count(*) AS sessions, sum(s2_add_to_cart) AS add_to_cart, sum(s3_begin_checkout) AS begin_checkout,
       sum(s6_purchase) AS purchase,
       round(sum(s6_purchase) / count(*), 5) AS conversion_rate
FROM ga4_sessions
GROUP BY ALL ORDER BY 1, 2;

-- 4. Data-quality checks on the real export: what a CRO analyst checks before trusting a funnel
-- output: ga4_data_quality
WITH p AS (SELECT * FROM ga4_events WHERE event_name = 'purchase'),
dup AS (
  SELECT ecom_transaction_id, count(*) AS n
  FROM p WHERE ecom_transaction_id IS NOT NULL AND ecom_transaction_id <> '(not set)'
  GROUP BY 1
)
SELECT 'purchase events' AS check_name, (SELECT count(*) FROM p)::DOUBLE AS value, 'events' AS unit
UNION ALL SELECT 'purchase events with a missing or (not set) transaction id',
       (SELECT count(*) FROM p WHERE ecom_transaction_id IS NULL OR ecom_transaction_id = '(not set)'), 'events'
UNION ALL SELECT 'distinct transaction ids', (SELECT count(*) FROM dup), 'ids'
UNION ALL SELECT 'transaction ids sent more than once', (SELECT count(*) FROM dup WHERE n > 1), 'ids'
UNION ALL SELECT 'extra purchase events from duplicated ids', (SELECT sum(n - 1) FROM dup WHERE n > 1), 'events'
UNION ALL SELECT 'sessions without a session_start event',
       (SELECT count(*) FROM ga4_sessions WHERE has_session_start = 0), 'sessions'
UNION ALL SELECT 'share of sessions without session_start',
       (SELECT avg(1 - has_session_start) FROM ga4_sessions), 'share'
UNION ALL SELECT 'share of sessions with channel not available ((data deleted), <Other>)',
       (SELECT avg((first_user_channel = 'Other / not available')::INT) FROM ga4_sessions), 'share'
UNION ALL SELECT 'purchase sessions without begin_checkout in the same session',
       (SELECT count(*) FROM ga4_sessions WHERE s6_purchase = 1 AND s3_begin_checkout = 0), 'sessions'
UNION ALL SELECT 'view_item_list events (list views barely tracked)',
       (SELECT count(*) FROM ga4_events WHERE event_name = 'view_item_list'), 'events'
UNION ALL SELECT 'view_cart events (not tracked in this export)',
       (SELECT count(*) FROM ga4_events WHERE event_name = 'view_cart'), 'events';

-- 5. Revenue with and without de-duplication on transaction id (the reconciliation rule)
-- output: ga4_revenue_dedup
WITH p AS (
  SELECT ecom_transaction_id, ecom_revenue_usd,
         row_number() OVER (PARTITION BY ecom_transaction_id ORDER BY event_timestamp) AS rn
  FROM ga4_events
  WHERE event_name = 'purchase' AND ecom_transaction_id IS NOT NULL AND ecom_transaction_id <> '(not set)'
)
SELECT round(sum(ecom_revenue_usd), 0)                        AS revenue_all_events_usd,
       round(sum(CASE WHEN rn = 1 THEN ecom_revenue_usd END), 0) AS revenue_dedup_usd,
       round(sum(ecom_revenue_usd) / sum(CASE WHEN rn = 1 THEN ecom_revenue_usd END) - 1, 4) AS inflation_share
FROM p;
