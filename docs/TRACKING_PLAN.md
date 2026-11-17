# GA4 e-commerce tracking plan for a Shopify store (template)

Generic plan based on Google's recommended e-commerce events for GA4 and Shopify's customer-events model.
It describes what a store like the one studied **should** send; it is not an audit of Tediber's tags
(we only observed which scripts load on the public homepage).

## Events
| Step | GA4 event | When | Key parameters |
|---|---|---|---|
| Listing seen | `view_item_list` | Category / collection page shown | `item_list_id`, `item_list_name`, `items[]` |
| Product clicked | `select_item` | Click on a product tile | `item_list_name`, `items[0]` |
| Product page | `view_item` | Product page shown | `currency`, `value`, `items[]` (`item_id`, `item_name`, `item_category`, `item_variant` = size, `price`) |
| Add to cart | `add_to_cart` | Item added | same + `quantity` |
| Cart | `view_cart` | Cart page or drawer opened | `value`, `items[]` |
| Checkout | `begin_checkout` | Checkout starts | `value`, `items[]`, `coupon` |
| Delivery | `add_shipping_info` | Delivery option chosen | `shipping_tier` (standard / room delivery / take-back / store) |
| Payment | `add_payment_info` | Payment method chosen | `payment_type` (card, split 3x / 4x / 10x / 12x / 24x, PayPal) |
| Order | `purchase` | Thank-you page / order confirmation | **`transaction_id`** (shop order number), `value`, `tax`, `shipping`, `currency`, `coupon`, `items[]` |
| Return | `refund` (server side) | Return accepted within the trial | `transaction_id`, `value`, `items[]` |

Custom dimensions worth adding for bedding: `trial_eligible` (100 / 30 nights), `bulky_item` (yes/no),
`delivery_fee_shown_on_pdp` (test flag), `experiment_id` and `variant_id` (exposure event from the testing tool).

## Data-quality rules
1. **One purchase per `transaction_id`.** De-duplicate in reporting (`row_number() over (partition by transaction_id)`, see
   `sql/04_reconciliation.sql`); in the real GA4 sample, 326 ids were sent more than once (+7.4 % revenue).
2. **Daily reconciliation with the back office**: orders and revenue ratio analytics / shop; alert if > 100 % or if
   the ratio moves by more than 3 points vs its 4-week median.
3. **No missing ids**: 906 purchase events of the real sample have no usable `transaction_id` - such events cannot be
   de-duplicated; fix at the source.
4. **Every session has a `session_start`** (1.4 % missing in the real sample) and a channel (21 % "data deleted / other" in
   the real sample: check consent mode and UTM rules).
5. **Tag changes go through the release log** with a before/after check of purchase counts (the simulated duplicate
   started with a tag-manager migration).
6. **Consent**: tags respect the visitor's consent choice; measured gaps are reported, not "fixed" by guessing.
7. **No personal data** in event parameters or URLs (e-mail, phone, name).

## QA before release
Tag Assistant / debug view on a staging order for each payment type; check one purchase event per order, `value`
equals the order total, items match; repeat on Safari iOS (the browser most often broken by payment widgets).
