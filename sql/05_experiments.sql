-- =====================================================================================================
-- 05 - A/B test read-out (SIMULATED testing-tool export, visitor level)
-- Per test and variant: visitors, add-to-cart rate, conversion, revenue, 100-night returns, net revenue
-- per visitor. First check: Sample Ratio Mismatch (SRM). With a planned 50/50 split, a chi-square above
-- 10.83 (p < 0.001, 1 degree of freedom) means the allocation is broken: the test is NOT read.
-- p-values, confidence intervals and the bootstrap are computed in Python (notebook / src/stats_tests.py).
-- =====================================================================================================

-- output: experiment_summary
WITH v AS (
  SELECT test_id, any_value(test_name) AS test_name, any_value(population) AS population,
         min(CAST(date AS DATE)) AS start_date, max(CAST(date AS DATE)) AS end_date, variant,
         sum(visitors) AS visitors, sum(add_to_cart_visitors) AS atc_visitors, sum(orders) AS orders,
         sum(revenue_eur) AS revenue_eur, sum(returned_orders) AS returned_orders,
         sum(returned_revenue_eur) AS returned_revenue_eur
  FROM experiments
  GROUP BY test_id, variant
),
t AS (
  SELECT *, sum(visitors) OVER (PARTITION BY test_id) AS test_visitors FROM v
)
SELECT *,
       visitors / test_visitors                               AS allocation_share,
       atc_visitors / visitors                                AS add_to_cart_rate,
       orders / visitors                                      AS conversion_rate,
       revenue_eur / visitors                                 AS revenue_per_visitor_eur,
       (revenue_eur - returned_revenue_eur) / visitors        AS net_revenue_per_visitor_eur,
       returned_orders / nullif(orders, 0)                    AS return_rate,
       -- SRM: chi-square of the observed split against 50/50 (same value on both rows of a test)
       sum(power(visitors - test_visitors / 2.0, 2) / (test_visitors / 2.0)) OVER (PARTITION BY test_id) AS srm_chi2
FROM t
ORDER BY test_id, variant;

-- output: experiment_daily
SELECT test_id, CAST(date AS DATE) AS d, variant, visitors, orders,
       sum(visitors) OVER w AS cum_visitors, sum(orders) OVER w AS cum_orders,
       sum(orders) OVER w / sum(visitors) OVER w AS cum_conversion_rate
FROM experiments
WINDOW w AS (PARTITION BY test_id, variant ORDER BY CAST(date AS DATE))
ORDER BY test_id, d, variant;
