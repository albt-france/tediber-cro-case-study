-- =====================================================================================================
-- 02 - Funnel by step (SIMULATED store): sessions -> category view -> product view -> add to cart
--      -> cart view -> checkout -> shipping -> payment -> order, with step-to-step pass rates.
-- Counts are sessions that reached each step (open funnel).
-- =====================================================================================================

-- 1. Whole period, one row per segment
-- output: funnel_segments
WITH f AS (
  SELECT CASE WHEN GROUPING(device) = 0 AND GROUPING(browser) = 0 THEN 'Device x browser'
              WHEN GROUPING(device) = 0 THEN 'Device'
              WHEN GROUPING(channel) = 0 THEN 'Channel'
              WHEN GROUPING(visitor_type) = 0 THEN 'Visitor type'
              WHEN GROUPING(entry_category) = 0 THEN 'Category'
              ELSE 'All' END AS dimension,
         CASE WHEN GROUPING(device) = 0 AND GROUPING(browser) = 0 THEN device || ' / ' || browser
              ELSE coalesce(device, channel, visitor_type, entry_category, 'All') END AS segment,
         sum(sessions) AS sessions, sum(category_views) AS category_views, sum(product_views) AS product_views,
         sum(add_to_cart) AS add_to_cart, sum(cart_views) AS cart_views, sum(checkout_starts) AS checkout_starts,
         sum(shipping_completed) AS shipping_completed, sum(payment_completed) AS payment_completed,
         sum(orders) AS orders, sum(revenue_eur) AS revenue_eur
  FROM sessions_daily
  GROUP BY GROUPING SETS ((), (device), (device, browser), (channel), (visitor_type), (entry_category))
)
SELECT *,
       product_views / sessions                     AS pass_product_view,
       add_to_cart / product_views                  AS pass_add_to_cart,
       checkout_starts / add_to_cart                AS pass_checkout,
       shipping_completed / checkout_starts         AS pass_shipping,
       payment_completed / shipping_completed       AS pass_payment,
       orders / payment_completed                   AS pass_order,
       orders / sessions                            AS conversion_rate,
       1 - shipping_completed / checkout_starts     AS shipping_step_abandonment,
       revenue_eur / sessions                       AS revenue_per_visit_eur
FROM f
ORDER BY dimension, sessions DESC;

-- 2. Monthly cube for the dashboard filters (device x channel x visitor type x category)
-- output: funnel_cube_monthly
SELECT date_trunc('month', CAST(date AS DATE))::DATE AS month, device, channel, visitor_type, entry_category,
       sum(sessions) AS sessions, sum(product_views) AS product_views, sum(add_to_cart) AS add_to_cart,
       sum(checkout_starts) AS checkout_starts, sum(shipping_completed) AS shipping_completed,
       sum(payment_completed) AS payment_completed, sum(orders) AS orders, round(sum(revenue_eur), 0) AS revenue_eur
FROM sessions_daily
GROUP BY ALL
ORDER BY ALL;
