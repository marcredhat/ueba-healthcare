# SDL PowerQuery quirks (this tenant)

Discovered while building the UEBA pack. Treat as the canonical "rules" for
authoring new PQs in this tenant.

## Functions / syntax
- **Hour bucket**: use `timebucket('1 hour')` in `group ... by hour_ts = timebucket('1 hour'), ...`. `bin(timestamp, 1h)` is **not** supported.
- **Conditional count**: `count(condition)`. `countif(condition)` is **not** supported and causes HTTP 500.
- **Conditional sum**: `sum(field)` works. `sum(if(cond, field, 0))` **causes 500** — split into a second metric or pre-aggregate.
- **JSON extraction**: parse the raw `message` string with regex, e.g.
  ```
  | parse '"username": "$entity_id{regex=[^"]+}$"' from message
  ```
  - For numeric values (no quotes in JSON): `'"record_count": $record_count{regex=[0-9]+}$'`
  - `json_object_value(json_object_value(message, 'a'), 'b')` works alone but **500s** when combined with `timebucket()` in a group.
  - `parse_jsonpath` is **not** supported in this tenant.

## Pipeline structure
- **All `parse` commands FIRST**, then `group`. Inserting `filter` or `extend` between `parse` and `group` silently drops rows (results return zero rows or 500).
- **`dcount(parsed_field)` 500s** post-group. Compute distinct counts via a 2-stage subquery (group by entity+field, then count groups) and join.

## Filtering after `group`
- **Null filter**: use `filter <col> = *` (means "not null"). `filter(isnotnull(col))` **500s** post-group.
- **String empty filter**: `filter( col != "" )` works.
- **Multi-condition with null check**: combining `isnotnull` with another condition 500s. If you need both null and non-empty filtering, just use `filter <col> = *` (it covers the null case; empty strings are rare in extracted JSON values).
- **`strlen(col)` is not supported**.

## What works (verified)
```powerquery
| filter( class_uid == 3002 )
| parse '"username": "$entity_id{regex=[^"]+}$"'    from message
| parse '"outcome": "$outcome{regex=[^"]+}$"'       from message
| parse '"event_type": "$event_type{regex=[^"]+}$"' from message
| group
    total = count(),
    fails = count( outcome == "failure" )
  by hour_ts = timebucket('1 hour'), entity_id
| filter entity_id = *
| extend fail_ratio = if( total > 0, 1.0 * fails / total, 0.0 )
| columns entity_id, hour_ts, total, fails, fail_ratio
```

## Open items
- 2-stage `dcount` queries for cardinality features (`12_distinct_count_features.pq`).
- Healthcare-specific peers using `actor.role` / `organization.hospital_id` as part
  of the signature (see `06_peers_dynamic.pq`).
