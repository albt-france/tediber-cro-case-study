-- =====================================================================================================
-- 01 - Weekly KPI report (SIMULATED store). One row per week x segment.
-- KPIs: sessions, conversion rate (per session and per user), average order value (AOV), revenue per visit
-- (RPV), add-to-cart rate, checkout abandonment, revenue net of 100-night returns.
-- Changes: week over week (LAG 1) and same week last year (LAG 52), inside each segment.
-- Weeks start on Monday; the last, incomplete week of the data is dropped.
-- =====================================================================================================

-- output: weekly_kpis
WITH sess AS (            -- weekly sums for every segment slice (GROUPING SETS = several GROUP BYs at once)
  SELECT date_trunc('week', CAST(date AS DATE))::DATE AS week_start,
         CASE WHEN GROUPING(device) = 0 THEN 'Device'
              WHEN GROUPING(channel) = 0 THEN 'Channel'
              WHEN GROUPING(visitor_type) = 0 THEN 'Visitor type'
              WHEN GROUPING(entry_category) = 0 THEN 'Category'
              ELSE 'All' END                                           AS dimension,
         coalesce(device, channel, visitor_type, entry_category, 'All') AS segment,
         count(DISTINCT CAST(date AS DATE)) AS days,
         sum(sessions) AS sessions, sum(users) AS users, sum(product_views) AS product_views,
         sum(add_to_cart) AS add_to_cart, sum(checkout_starts) AS checkout_starts,
         sum(orders) AS orders, sum(revenue_eur) AS revenue_eur
  FROM sessions_daily
  GROUP BY GROUPING SETS ((1), (1, device), (1, channel), (1, visitor_type), (1, entry_category))
),
ret AS (                   -- returns, attached to the week of the ORDER (cohort view), observed so far
  SELECT date_trunc('week', CAST(date AS DATE))::DATE AS week_start,
         CASE WHEN GROUPING(device) = 0 THEN 'Device'
              WHEN GROUPING(channel) = 0 THEN 'Channel'
              WHEN GROUPING(visitor_type) = 0 THEN 'Visitor type'
              WHEN GROUPING(category) = 0 THEN 'Category'
              ELSE 'All' END                                     AS dimension,
         coalesce(device, channel, visitor_type, category, 'All') AS segment,
         sum(CASE WHEN returned THEN basket_eur ELSE 0 END)      AS returned_revenue_eur,
         sum(returned::INT)                                      AS returned_orders
  FROM orders
  GROUP BY GROUPING SETS ((1), (1, device), (1, channel), (1, visitor_type), (1, category))
),
k AS (
  SELECT s.week_start, s.dimension, s.segment, s.sessions, s.users, s.orders,
         round(s.revenue_eur, 2)                                        AS revenue_eur,
         round(coalesce(r.returned_revenue_eur, 0), 2)                  AS returned_revenue_eur,
         s.orders / s.sessions                                          AS conversion_rate,
         s.orders / s.users                                             AS conversion_per_user,
         s.revenue_eur / nullif(s.orders, 0)                            AS aov_eur,
         s.revenue_eur / s.sessions                                     AS revenue_per_visit_eur,
         (s.revenue_eur - coalesce(r.returned_revenue_eur, 0)) / s.sessions AS net_revenue_per_visit_eur,
         s.add_to_cart / s.sessions                                     AS add_to_cart_rate,
         1 - s.orders / nullif(s.checkout_starts, 0)                    AS checkout_abandonment,
         coalesce(r.returned_orders, 0) / nullif(s.orders, 0)           AS return_rate_observed
  FROM sess s LEFT JOIN ret r USING (week_start, dimension, segment)
  WHERE s.days = 7
)
SELECT *,
       -- week over week and year over year, as relative changes (0.05 = +5 %)
       conversion_rate / LAG(conversion_rate, 1) OVER w - 1                    AS conversion_rate_wow,
       conversion_rate / LAG(conversion_rate, 52) OVER w - 1                   AS conversion_rate_yoy,
       sessions / LAG(sessions, 1) OVER w - 1                                  AS sessions_wow,
       sessions / LAG(sessions, 52) OVER w - 1                                 AS sessions_yoy,
       revenue_per_visit_eur / LAG(revenue_per_visit_eur, 1) OVER w - 1        AS rpv_wow,
       revenue_per_visit_eur / LAG(revenue_per_visit_eur, 52) OVER w - 1       AS rpv_yoy,
       aov_eur / LAG(aov_eur, 1) OVER w - 1                                    AS aov_wow,
       add_to_cart_rate / LAG(add_to_cart_rate, 1) OVER w - 1                  AS add_to_cart_rate_wow,
       checkout_abandonment - LAG(checkout_abandonment, 1) OVER w              AS checkout_abandonment_wow_pts
FROM k
WINDOW w AS (PARTITION BY dimension, segment ORDER BY week_start)
ORDER BY week_start, dimension, segment;
