-- =====================================================================================================
-- 04 - Analytics vs shop reconciliation (SIMULATED store)
-- The shop back-office is the reference for orders and revenue. Analytics normally sees a little less
-- (consent refusals, ad-blockers). A ratio ABOVE 1 is a red flag: purchases counted twice.
-- Rule: de-duplicate purchase events on transaction_id before any revenue KPI.
-- =====================================================================================================

-- output: reconciliation_daily
WITH d AS (
  SELECT CAST(date AS DATE) AS d, shop_orders, shop_revenue_eur, analytics_purchase_events,
         analytics_transactions, analytics_revenue_eur,
         sum(analytics_revenue_eur) OVER w7 / nullif(sum(shop_revenue_eur) OVER w7, 0)     AS revenue_ratio_7d,
         sum(analytics_purchase_events) OVER w7 / nullif(sum(shop_orders) OVER w7, 0)      AS events_per_order_7d,
         sum(analytics_purchase_events - analytics_transactions) OVER w7
           / nullif(sum(analytics_purchase_events) OVER w7, 0)                              AS duplicate_share_7d
  FROM ga4_vs_shop_daily
  WINDOW w7 AS (ORDER BY CAST(date AS DATE) RANGE BETWEEN INTERVAL 6 DAYS PRECEDING AND CURRENT ROW)
)
SELECT *,
       -- the dedup rule: count each transaction once, value it at the shop's average basket of the day
       analytics_transactions * shop_revenue_eur / nullif(shop_orders, 0) AS analytics_revenue_dedup_eur,
       (revenue_ratio_7d > 1.0 OR duplicate_share_7d > 0.02) AS alert
FROM d
ORDER BY d;

-- output: reconciliation_incidents
WITH f AS (
  SELECT d, revenue_ratio_7d, duplicate_share_7d,
         d - CAST(row_number() OVER (ORDER BY d) AS INTEGER) AS island
  FROM (SELECT CAST(date AS DATE) AS d,
               sum(analytics_revenue_eur) OVER w7 / nullif(sum(shop_revenue_eur) OVER w7, 0) AS revenue_ratio_7d,
               sum(analytics_purchase_events - analytics_transactions) OVER w7
                 / nullif(sum(analytics_purchase_events) OVER w7, 0) AS duplicate_share_7d
        FROM ga4_vs_shop_daily
        WINDOW w7 AS (ORDER BY CAST(date AS DATE) RANGE BETWEEN INTERVAL 6 DAYS PRECEDING AND CURRENT ROW))
  WHERE revenue_ratio_7d > 1.0 OR duplicate_share_7d > 0.02
)
SELECT min(d) AS first_day, max(d) AS last_day, count(*) AS days_flagged,
       max(revenue_ratio_7d) AS max_revenue_ratio, max(duplicate_share_7d) AS max_duplicate_share,
       (SELECT string_agg(strftime(release_date, '%Y-%m-%d') || ' ' || area || ': ' || description, ' | ')
        FROM releases WHERE area = 'Tracking' AND CAST(release_date AS DATE) BETWEEN min(f.d) - 10 AND max(f.d) + 1)
         AS candidate_releases
FROM f
GROUP BY island
HAVING count(*) >= 3
ORDER BY first_day;

-- output: reconciliation_weekly
SELECT date_trunc('week', CAST(date AS DATE))::DATE AS week_start,
       sum(shop_orders) AS shop_orders, sum(analytics_purchase_events) AS analytics_purchase_events,
       sum(analytics_transactions) AS analytics_transactions,
       round(sum(shop_revenue_eur), 0) AS shop_revenue_eur, round(sum(analytics_revenue_eur), 0) AS analytics_revenue_eur,
       sum(analytics_revenue_eur) / sum(shop_revenue_eur) AS revenue_ratio
FROM ga4_vs_shop_daily
GROUP BY 1 ORDER BY 1;
