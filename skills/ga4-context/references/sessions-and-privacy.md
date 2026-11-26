# Sessions, metrics and privacy tiers

## Definitions
- **Session**: `user_pseudo_id` + the integer event parameter `ga_session_id`. Get it with
  `(SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id')`.
- **Engaged session**: lasted more than 10 seconds, OR has 2 or more `page_view` events, OR contains a `purchase`.
- **Active buyer (28 days)**: a distinct `user_pseudo_id` with at least one `purchase` in the 28 days up to the target date.
- **Cart conversion rate**: sessions containing a `purchase` divided by sessions containing an `add_to_cart`.
- **Item-level questions**: flatten with `CROSS JOIN UNNEST(items) AS item`.

## Sensitivity tiers
- **C1 (internal)**: `device.*`, `traffic_source.*` and all other unclassified columns. No extra restriction.
- **C2 (pseudonymous)**: `user_pseudo_id`. Stays in the analytics project; never joined to CRM or email tables.
- **C3 (restricted)**: `geo.city`, `geo.metro`. Never shown at city level; publish only aggregated to `geo.region` or `geo.country`.
