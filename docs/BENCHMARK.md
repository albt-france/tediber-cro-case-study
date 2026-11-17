# E-commerce good practices - short, sourced summary

Summarised in our own words from public sources (read 17 Nov 2026); no text copied. Each line says how it is
used in this study.

| # | Practice | Source | Used where |
|---|---|---|---|
| 1 | Unexpected extra costs (shipping, taxes, fees) are the most cited reason to abandon a checkout: 40 % of US shoppers who abandoned, in Baymard's survey; average documented cart abandonment 70.22 % (50 studies) | Baymard Institute, cart-abandonment-rate list (updated 28 Oct 2026) | Test C (bulky delivery fee shown on the product page) |
| 2 | Show the delivery date or delay early, on the product page | Baymard (slow delivery is the 2nd reason, 20 %) | Backlog B07 |
| 3 | Reassurance (returns, trial, payment security) close to the main call to action | Baymard checkout and product-page research (trust is the 3rd reason, 19 %) | Test B |
| 4 | Keep the main action reachable on mobile (sticky call to action on long pages) | Baymard mobile product-page research | Test A |
| 5 | Compare products side by side when the choice is technical | Baymard product-comparison research | Test D (and its v2) |
| 6 | Track the recommended GA4 e-commerce events with a unique `transaction_id`; de-duplicate purchases | Google Analytics help: "Measure ecommerce" / recommended events | Tracking plan, reconciliation |
| 7 | Use Shopify's customer events / web pixels for checkout tracking (checkout pages do not run theme scripts) | Shopify help: customer events | Tracking plan |
| 8 | Fix the test duration and sample size in advance; do not stop at the first significant day | Standard A/B testing statistics (fixed-horizon tests) | Calculator, peeking simulation |
| 9 | Check the sample ratio before reading any test | Experimentation literature on SRM | Test B |
| 10 | Good page speed: Core Web Vitals "good" thresholds are LCP <= 2.5 s, INP <= 200 ms, CLS <= 0.1 at the 75th percentile of real users | web.dev, Core Web Vitals | Lighthouse page, backlog B05 |

Links: `https://baymard.com/lists/cart-abandonment-rate` · `https://support.google.com/analytics/answer/12200568` ·
`https://help.shopify.com/en/manual/promoting-marketing/pixels` · `https://web.dev/articles/vitals`
