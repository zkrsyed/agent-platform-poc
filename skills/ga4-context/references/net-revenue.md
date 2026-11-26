# Daily net revenue, final days only

Use when a question asks for revenue **per day** over a period that reaches the end of the data (for example "daily net revenue for January").

1. Net merch revenue = `SUM(ecommerce.purchase_revenue_in_usd) - SUM(IFNULL(ecommerce.refund_value_in_usd, 0))`. USD columns only.
2. A day is final 72 hours after it ends: **drop the last 3 days**. The data ends on 2021-01-31, so January's final days are 2021-01-01 to 2021-01-28.
3. Filter on `event_date_dt`, never on the string `event_date`.
4. Group by `event_date_dt` and order by it.
5. In the answer, say that the last 3 days were left out because they are not final yet.

```sql
SELECT event_date_dt,
       SUM(ecommerce.purchase_revenue_in_usd) - SUM(IFNULL(ecommerce.refund_value_in_usd, 0)) AS net_merch_revenue_usd
FROM `kc-okf-poc-261122.ga4_sample.events`
WHERE event_date_dt BETWEEN '2021-01-01' AND DATE_SUB('2021-01-31', INTERVAL 3 DAY)
GROUP BY event_date_dt
ORDER BY event_date_dt
```

Traps seen before: using `purchase_revenue` (local currency); forgetting `IFNULL` on refunds; including 2021-01-29 to 2021-01-31.
