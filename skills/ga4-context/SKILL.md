---
name: ga4-context
description: Rules and definitions for querying the Google Merchandise Store GA4 table `kc-okf-poc-261122.ga4_sample.events` correctly. Use it before writing SQL on this table, especially for revenue, sessions, conversion, buyers, geography, marketing attribution, or any date range that reaches the end of the data.
---

# GA4 merchandise store: query rules

Source: the data team's governance and metrics pages in Knowledge Catalog (checked against the table on 2026-11-25).

## Always apply these to `kc-okf-poc-261122.ga4_sample.events`

1. **Filter on the partition column `event_date_dt`** (a DATE). Never on the string `event_date`, and never `_TABLE_SUFFIX`: this is one partitioned table, not daily shards.
2. The data covers **2020-11-01 to 2021-01-31** (92 days). Dates outside that return no rows.
3. **Revenue uses the USD columns only.** Net merch revenue = `SUM(ecommerce.purchase_revenue_in_usd) - SUM(IFNULL(ecommerce.refund_value_in_usd, 0))`. Refunds are NULL on every purchase row, so without `IFNULL` the result is NULL.
4. **A day is final 72 hours after it ends** (data policy). For daily revenue, or any figure called "final", over a period that reaches the end of the data, leave out the last 3 days (2021-01-29 to 2021-01-31) and say so in the answer.
5. **Marketing attribution** (anything grouped by `traffic_source.*`): exclude rows where `traffic_source.source = '(data deleted)'`.
6. **Privacy:** `geo.city` and `geo.metro` must never be shown at city or metro level. Roll up to `geo.region` or `geo.country`. `user_pseudo_id` must not be exported or joined to CRM or email data.
7. `event_params`, `user_properties` and `items` are nested arrays: read them with `UNNEST()`.

## More detail (read only when the question needs it)

- `references/net-revenue.md`: the daily net revenue playbook, with a SQL example.
- `references/sessions-and-privacy.md`: sessions, engaged sessions, active buyers, cart conversion, and the C1/C2/C3 sensitivity tiers.
