# Assumptions of the simulated store (SIMULATED)

A fictional direct-to-consumer bedding store "modelled on public information": product ranges, a 100-night trial,
split payment, bulky items, a November "Black Month". **None of these numbers are Tediber's.**

| Topic | Assumption | Why / calibration |
|---|---|---|
| Period | 1 Jun 2025 - 30 Nov 2026, day by day; "today" for returns = 30 Nov 2026 | 18 months: one full year of history before the second Black Month |
| Volume | ~8,000 sessions/day at base, +9 %/year trend, winter +8 % seasonality; 5.4 M sessions, 68 k orders, EUR 26 M over 18 months (~EUR 18 M/year) | Same order of magnitude as the 2020 revenue published in the register (EUR 23.6 M, stores included) |
| Device | mobile 60 %, desktop 34 %, tablet 6 %; Safari iOS 52 % of mobile | Public device-mix benchmarks; real GA4 sample has 40 % mobile (a 2020 B2C merch store) |
| Channels | organic 28 %, paid search 22 %, paid social 14 %, e-mail/CRM 10 %, direct 17 %, affiliation 9 % | Typical DTC mix; returning-visitor share by channel 12 %-70 % |
| Entry category | mattress 38 %, bed base & bed 16 %, pillow & duvet 22 %, bed linen 12 %, kids 7 %, sofa 5 % | Catalogue shares seen in the public sitemap, weighted to the core product |
| Funnel | product view 48 % of sessions; add-to-cart 6.8 % of product views (x0.45 paid social ... x1.55 returning); checkout 58 % of carts; shipping 80 % (60 % for bulky items); payment 82 %; order 80 % | Step ratios close to the real GA4 sample (conversion 1.35 %, checkout abandonment 56 %) -> simulated conversion 1.25 % |
| Basket | log-normal, mean EUR 780 mattress, 620 bed base, 165 pillow/duvet, 120 linen, 330 kids, 1,350 sofa | Price ranges read on 10 public product pages |
| Split payment | 38 % of baskets >= EUR 400, 8 % of EUR 50-400 | Split payment offered from EUR 50 (public delivery page) |
| Returns | 8.5 % mattresses, 6 % sofas, 4-5 % other, 3 % linen (30-night window); return 8-103 days after the order | 100-night trial; returns after 30 Nov 2026 are not observed yet |
| Promotions | summer sales (late Jun-Jul), winter sales (Jan), Black Month (all November, Black Friday week x1.35): traffic x1.25-x1.9, conversion x1.10-x1.22, basket x0.86-x0.92 | Public "Black Month: jusqu'à -40 %" banner on 17 Nov 2026 |
| Analytics vs shop | analytics records 96.5 % of shop orders (consent, ad-blockers); 0.4 % duplicates normally | Usual gap of a client-side tag vs back office |
| Tests | 4 tests, visitor level, 50/50; true effects: A add-to-cart +7.5 %; B none (redirect loses 4 % of variant visitors); C conversion +20 %, add-to-cart -4 %; D conversion +6.5 %, returns x1.5 | Effects small enough to need a power calculation |

## The 8 planted events (to be found by the monitoring, scored at the end)
1. Payment step -30 % on Safari iOS only, 10-18 Mar 2026, after a split-payment widget release.
2. Mattress product pages +1.4 s mobile LCP, add-to-cart -22 % on mobile/tablet only, 12 May - 22 Jun 2026.
3. Bulky items: shipping-step abandonment twice the other categories (whole period).
4. False signal: paid-social sessions x4 for two weeks (31 Aug - 13 Sep 2026); every segment stable.
5. Purchase event sent twice for ~11 % of orders, 7 Jul - 3 Aug 2026.
6. Sample ratio mismatch in test B (48/52).
7. Test D wins on conversion but loses on returns.
8. Black Month 2026: normal seasonality, not an anomaly.
The answer key (`data/_hidden_truth.csv`) was used once by `src/analyse.py` to score the detection
(`data/processed/detection_scorecard.csv`) and is not published.
