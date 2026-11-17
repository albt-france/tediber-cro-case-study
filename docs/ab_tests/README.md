# A/B tests - process (SIMULATED store)

| Test | Brief | Read-out | Decision |
|---|---|---|---|
| A - Sticky add-to-cart button on mobile product pages | [brief](test_A_sticky_add_to_cart_mobile_brief.md) | [read-out](test_A_sticky_add_to_cart_mobile_readout.md) | ship |
| B - "100-night trial" reassurance next to the button | [brief](test_B_trial_reassurance_near_button_brief.md) | [read-out](test_B_trial_reassurance_near_button_readout.md) | invalid (SRM): fix and relaunch |
| C - Delivery fee shown on bulky-item product pages | [brief](test_C_bulky_delivery_fee_on_product_page_brief.md) | [read-out](test_C_bulky_delivery_fee_on_product_page_readout.md) | ship |
| D - Mattress comparator | [brief](test_D_mattress_comparator_brief.md) | [read-out](test_D_mattress_comparator_readout.md) | iterate |

## Lifecycle
1. **Idea** in the backlog (Excel "CRO backlog", ICE / RICE) with its evidence (data, audit, benchmark).
2. **Brief**: problem, hypothesis "Because we saw X, we believe Y will cause Z, measured by K", variants, primary KPI,
   guardrails, sample size and duration from the calculator (Excel "Test calculator" or `src/stats_tests.py`).
3. **QA before launch** (checklist in each brief), then a 24-48 h allocation check.
4. **Run to the planned end** - no stop on the first significant day: checking every day and stopping at the first
   p < 0.05 turns a 5 % false-positive rate into ~27 % (A/A simulation, `data/processed/peeking.csv`).
5. **Read**: SRM first, then the primary KPI (z test, 95 % CI), then guardrails (net revenue per visitor by bootstrap,
   100-night return rate).
6. **Decide** with the rule written in advance: SRM -> invalid; primary up and no guardrail breached -> ship; primary up
   but a guardrail breached -> iterate; otherwise drop.
7. **Document** in the test log (Excel "Test log") with the learning, and re-read returns after 100 nights.
