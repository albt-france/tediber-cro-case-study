-- =====================================================================================================
-- 03 - Anomaly detection (SIMULATED store)
-- For every slice (all traffic, device, device x browser, channel, category, device x category, visitor
-- type) and every funnel rate, each day:
--   rate      = 7-day trailing rate (sum of numerators / sum of denominators: smooths the weekday cycle)
--   baseline  = median of the same rate 7, 14, ..., 56 days earlier (8 weeks, same weekday), skipping
--               windows that touch a promotion (sales, Black Month) so a promo never pollutes the baseline
--   promo     = inside a promotion the expected value is last year's rate for the same promo, scaled by
--               how the regular baseline moved since then; with no prior year, no score (not an alert)
--   robust z  = (rate - expected) / sigma, sigma = max(1.4826 x MAD of the 8 values, binomial noise)
--               (inside a promo, the noise of last year's value is added)
--   alert     = |z| >= 3.5 AND |relative change| >= 10 % AND denominator >= 150, for 5 days or more
-- Incidents are linked to the releases of the 10 days before they start (the release log is the only
-- lead to a cause). Before an incident is opened, two checks:
--   - traffic mix: if the channel mix moved (total variation distance of channel shares >= 0.08 vs the
--     4 previous weeks) and no channel slice shows the same alert, the move is a MIX effect, not a break
--     (the rate / mix decomposition by channel quantifies it);
--   - recovery: an alert in the opposite direction right after an incident on the same slice is the fix
--     landing while the baseline still remembers the bad weeks.
-- =====================================================================================================

CREATE OR REPLACE TABLE promo_days AS
SELECT DISTINCT CAST(d AS DATE) AS d
FROM promo_calendar, generate_series(start_date, end_date, INTERVAL 1 DAY) AS t(d);

-- 1. daily counts per slice (GROUPING SETS) and per KPI (long format)
CREATE OR REPLACE TABLE slice_daily AS
WITH g AS (
  SELECT CAST(date AS DATE) AS d,
         CASE WHEN GROUPING(device) = 0 AND GROUPING(browser) = 0 THEN 'Device x browser'
              WHEN GROUPING(device) = 0 AND GROUPING(entry_category) = 0 THEN 'Device x category'
              WHEN GROUPING(device) = 0 THEN 'Device'
              WHEN GROUPING(channel) = 0 THEN 'Channel'
              WHEN GROUPING(entry_category) = 0 THEN 'Category'
              WHEN GROUPING(visitor_type) = 0 THEN 'Visitor type'
              ELSE 'All' END AS dimension,
         concat_ws(' / ', device, browser, channel, entry_category, visitor_type) AS slice,
         sum(sessions) sessions, sum(product_views) pdp, sum(add_to_cart) atc, sum(checkout_starts) chk,
         sum(shipping_completed) ship, sum(payment_completed) pay, sum(orders) orders
  FROM sessions_daily
  GROUP BY GROUPING SETS ((1), (1, device), (1, device, browser), (1, channel), (1, entry_category),
                          (1, device, entry_category), (1, visitor_type))
),
grid AS (                  -- complete calendar per slice, so that LAG(x, 7) is exactly 7 days back
  SELECT s.dimension, s.slice, c.d
  FROM (SELECT DISTINCT dimension, slice FROM g) s,
       (SELECT DISTINCT d FROM g) c
),
filled AS (
  SELECT grid.dimension, CASE WHEN grid.slice = '' THEN 'All traffic' ELSE grid.slice END AS slice, grid.d,
         coalesce(sessions, 0) sessions, coalesce(pdp, 0) pdp, coalesce(atc, 0) atc, coalesce(chk, 0) chk,
         coalesce(ship, 0) ship, coalesce(pay, 0) pay, coalesce(orders, 0) orders
  FROM grid LEFT JOIN g USING (dimension, slice, d)
)
SELECT dimension, slice, d, kpi, num, den FROM filled,
  (VALUES ('conversion rate'), ('add-to-cart rate'), ('shipping step'), ('payment step'), ('order step')) k(kpi),
  LATERAL (SELECT CASE kpi WHEN 'conversion rate' THEN orders WHEN 'add-to-cart rate' THEN atc
                           WHEN 'shipping step' THEN ship WHEN 'payment step' THEN pay ELSE orders END AS num,
                  CASE kpi WHEN 'conversion rate' THEN sessions WHEN 'add-to-cart rate' THEN pdp
                           WHEN 'shipping step' THEN chk WHEN 'payment step' THEN ship ELSE pay END AS den);

-- 2. trailing 7-day rate, promo flags, same-weekday lags, expected value and robust z
CREATE OR REPLACE TABLE slice_scores AS
WITH r AS (
  SELECT s.*,
         sum(num) OVER w7 AS num7, sum(den) OVER w7 AS den7,
         max(CASE WHEN p.d IS NOT NULL THEN 1 ELSE 0 END) OVER w7 AS win_promo
  FROM slice_daily s LEFT JOIN promo_days p USING (d)
  WINDOW w7 AS (PARTITION BY dimension, slice, kpi ORDER BY d RANGE BETWEEN INTERVAL 6 DAYS PRECEDING AND CURRENT ROW)
),
r2 AS (
  SELECT *, num7 / nullif(den7, 0) AS rate FROM r
),
l AS (
  SELECT *,
         -- the 8 same-weekday values of the past 8 weeks, kept only if their window has no promo day
         list_filter(list_value(
             CASE WHEN LAG(win_promo, 7) OVER w = 0 THEN LAG(rate, 7) OVER w END,
             CASE WHEN LAG(win_promo, 14) OVER w = 0 THEN LAG(rate, 14) OVER w END,
             CASE WHEN LAG(win_promo, 21) OVER w = 0 THEN LAG(rate, 21) OVER w END,
             CASE WHEN LAG(win_promo, 28) OVER w = 0 THEN LAG(rate, 28) OVER w END,
             CASE WHEN LAG(win_promo, 35) OVER w = 0 THEN LAG(rate, 35) OVER w END,
             CASE WHEN LAG(win_promo, 42) OVER w = 0 THEN LAG(rate, 42) OVER w END,
             CASE WHEN LAG(win_promo, 49) OVER w = 0 THEN LAG(rate, 49) OVER w END,
             CASE WHEN LAG(win_promo, 56) OVER w = 0 THEN LAG(rate, 56) OVER w END), x -> x IS NOT NULL) AS hist
  FROM r2
  WINDOW w AS (PARTITION BY dimension, slice, kpi ORDER BY d)
),
b AS (
  SELECT *, CASE WHEN len(hist) >= 4 THEN list_median(hist) END AS base_regular FROM l
),
m AS (
  SELECT *,
         list_median(list_transform(hist, x -> abs(x - base_regular))) AS mad,
         LAG(rate, 364) OVER w                                         AS rate_ly,
         LAG(win_promo, 364) OVER w                                    AS promo_ly,
         LAG(base_regular, 364) OVER w                                 AS base_regular_ly,
         LAG(den7, 364) OVER w                                         AS den7_ly
  FROM b
  WINDOW w AS (PARTITION BY dimension, slice, kpi ORDER BY d)
),
e AS (
  SELECT *,
         CASE WHEN win_promo = 0 THEN base_regular
              WHEN promo_ly = 1 AND base_regular_ly > 0 THEN rate_ly * base_regular / base_regular_ly
         END AS expected
  FROM m
),
s AS (
  SELECT dimension, slice, kpi, d, num7, den7, rate, win_promo, base_regular, expected,
         greatest(1.4826 * coalesce(mad, 0),
                  sqrt(greatest(expected * (1 - expected), 0)
                       * (1 / nullif(den7, 0) + CASE WHEN win_promo = 1 THEN 1 / nullif(den7_ly, 0) ELSE 0 END)))
           AS sigma
  FROM e
)
SELECT *, (rate - expected) / nullif(sigma, 0) AS z, rate / nullif(expected, 0) - 1 AS rel_change,
       coalesce(abs((rate - expected) / nullif(sigma, 0)) >= 3.5 AND abs(rate / nullif(expected, 0) - 1) >= 0.10
                AND den7 >= 150, FALSE) AS flagged
FROM s;

-- 3. flagged days -> incidents (gaps and islands: consecutive flagged days share the same d - row_number)
CREATE OR REPLACE TABLE incidents AS
WITH f AS (
  SELECT *, d - CAST(row_number() OVER (PARTITION BY dimension, slice, kpi ORDER BY d) AS INTEGER) AS island
  FROM slice_scores
  WHERE flagged
)
SELECT dimension, slice, kpi,
       min(d) AS first_day, max(d) AS last_day, count(*) AS days_flagged,
       max(win_promo) AS in_promo,
       arg_max(rel_change, abs(z)) AS rel_change_at_peak, arg_max(z, abs(z)) AS z_at_peak,
       arg_max(rate, abs(z)) AS rate_at_peak, arg_max(expected, abs(z)) AS expected_at_peak
FROM f
GROUP BY dimension, slice, kpi, island
HAVING count(*) >= 5;

-- 4. traffic-mix monitor: how far the channel mix of the last 7 days is from the 4 weeks before
CREATE OR REPLACE TABLE channel_mix AS
WITH c AS (
  SELECT CAST(date AS DATE) AS d, channel, sum(sessions) AS sessions
  FROM sessions_daily GROUP BY ALL
),
w AS (
  SELECT d, channel,
         sum(sessions) OVER (PARTITION BY channel ORDER BY d
                             RANGE BETWEEN INTERVAL 6 DAYS PRECEDING AND CURRENT ROW) AS s_cur,
         sum(sessions) OVER (PARTITION BY channel ORDER BY d
                             RANGE BETWEEN INTERVAL 34 DAYS PRECEDING AND INTERVAL 7 DAYS PRECEDING) AS s_base
  FROM c
),
sh AS (
  SELECT d, channel, s_cur / sum(s_cur) OVER (PARTITION BY d) AS share_cur,
         s_base / sum(s_base) OVER (PARTITION BY d) AS share_base
  FROM w WHERE d >= DATE '2025-07-05'          -- the base window needs 4 full weeks of history
)
SELECT d, 0.5 * sum(abs(share_cur - share_base)) AS mix_distance,
       arg_max(channel, share_cur - share_base) AS channel_gaining
FROM sh GROUP BY d;

CREATE OR REPLACE TABLE mix_episodes AS
WITH f AS (
  SELECT *, d - CAST(row_number() OVER (ORDER BY d) AS INTEGER) AS island
  FROM channel_mix WHERE mix_distance >= 0.08
)
SELECT min(d) AS first_day, max(d) AS last_day, max(mix_distance) AS max_mix_distance,
       arg_max(channel_gaining, mix_distance) AS channel_gaining
FROM f GROUP BY island HAVING count(*) >= 3;

-- 5. rate / mix decomposition of the topline conversion for each mix episode, by channel:
--    change = sum(share_before x (cr_during - cr_before))     [rate effect: conversion moved inside channels]
--           + sum((share_during - share_before) x cr_during)  [mix effect: channels weigh more or less]
CREATE OR REPLACE TABLE mix_decomposition AS
WITH seg AS (
  SELECT e.first_day, e.last_day, s.channel,
         sum(CASE WHEN CAST(s.date AS DATE) BETWEEN e.first_day - 6 AND e.last_day THEN s.sessions END) AS sess_cur,
         sum(CASE WHEN CAST(s.date AS DATE) BETWEEN e.first_day - 6 AND e.last_day THEN s.orders END)   AS ord_cur,
         sum(CASE WHEN CAST(s.date AS DATE) BETWEEN e.first_day - 34 AND e.first_day - 7 THEN s.sessions END) AS sess_base,
         sum(CASE WHEN CAST(s.date AS DATE) BETWEEN e.first_day - 34 AND e.first_day - 7 THEN s.orders END)   AS ord_base
  FROM mix_episodes e, sessions_daily s
  GROUP BY ALL
),
w AS (
  SELECT *, sess_cur / sum(sess_cur) OVER (PARTITION BY first_day) AS w_cur,
            sess_base / sum(sess_base) OVER (PARTITION BY first_day) AS w_base,
            ord_cur / sess_cur AS r_cur, ord_base / sess_base AS r_base
  FROM seg
)
SELECT first_day, last_day, channel, w_base AS share_before, w_cur AS share_during, r_base AS cr_before,
       r_cur AS cr_during, w_base * (r_cur - r_base) AS rate_effect, (w_cur - w_base) * r_cur AS mix_effect,
       sum(ord_base) OVER (PARTITION BY first_day) / sum(sess_base) OVER (PARTITION BY first_day) AS topline_cr_before,
       sum(ord_cur) OVER (PARTITION BY first_day) / sum(sess_cur) OVER (PARTITION BY first_day)   AS topline_cr_during
FROM w ORDER BY first_day, channel;

-- output: mix_decomposition
SELECT * FROM mix_decomposition;

-- output: channel_mix
SELECT * FROM channel_mix ORDER BY d;

-- 6. incident log with a status a human would write
-- output: anomaly_incidents
WITH rel AS (
  SELECT i.dimension, i.slice, i.kpi, i.first_day,
         string_agg(strftime(r.release_date, '%Y-%m-%d') || ' ' || r.area || ': ' || r.description, ' | '
                    ORDER BY r.release_date) AS candidate_releases
  FROM incidents i JOIN releases r
    ON CAST(r.release_date AS DATE) BETWEEN i.first_day - 10 AND i.first_day
  GROUP BY ALL
),
flags AS (
  SELECT i.*,
         EXISTS (SELECT 1 FROM mix_episodes m
                 WHERE i.first_day <= m.last_day + 6 AND i.last_day >= m.first_day) AS during_mix,
         EXISTS (SELECT 1 FROM incidents c
                 WHERE c.dimension = 'Channel' AND c.kpi = i.kpi
                   AND c.first_day <= i.last_day AND c.last_day >= i.first_day
                   AND sign(c.z_at_peak) = sign(i.z_at_peak)) AS seen_in_a_channel,
         EXISTS (SELECT 1 FROM incidents p
                 WHERE p.slice = i.slice AND p.kpi = i.kpi
                   AND p.last_day BETWEEN i.first_day - 21 AND i.first_day - 1
                   AND sign(p.z_at_peak) = -sign(i.z_at_peak)) AS follows_opposite
  FROM incidents i
)
SELECT f.dimension, f.slice, f.kpi, f.first_day, f.last_day, f.days_flagged, f.in_promo,
       f.rel_change_at_peak, f.z_at_peak, f.rate_at_peak, f.expected_at_peak, rel.candidate_releases,
       CASE WHEN f.during_mix AND NOT f.seen_in_a_channel THEN 'explained: traffic mix, no incident opened'
            WHEN f.follows_opposite THEN 'recovery after a fix'
            ELSE 'open: investigate' END AS status
FROM flags f LEFT JOIN rel USING (dimension, slice, kpi, first_day)
ORDER BY f.first_day, f.dimension, f.slice;

-- 7. series kept for the charts (a few slices only)
-- output: anomaly_series
SELECT dimension, slice, kpi, d, rate, expected, z, win_promo, flagged
FROM slice_scores
WHERE (slice = 'All traffic' AND kpi IN ('conversion rate', 'add-to-cart rate'))
   OR (slice IN ('mobile / Safari iOS', 'mobile / Chrome') AND kpi = 'payment step')
   OR (slice IN ('mobile / Mattress', 'desktop / Mattress') AND kpi = 'add-to-cart rate')
   OR (dimension = 'Channel' AND kpi = 'conversion rate')
ORDER BY slice, kpi, d;
