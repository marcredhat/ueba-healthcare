# SDL PowerQuery quirks (this tenant)

Discovered while building and running the UEBA pack end-to-end. Treat as the
canonical "rules" for authoring new PQs in this tenant.

## Execution model

- **Event Search UI is read-only for writes.** A query ending in
  `| savelookup '...'` returns "1 row · N bytes" metadata in the UI but
  **does not persist anything**. Use the PowerQuery API to actually write.
- **API endpoint**: `POST {tenant}/api/powerQuery` with body
  `{"query": "...", "startTime": "24h", "priority": "low"}`. Auth header
  uses the **Log Write** key (not Config Write — that token "does not grant
  View logs permission" and the call 403s).
- **Query body is capped at 15,000 chars.** Bigger queries return
  `error/client/badParam/tooLarge`. Split into per-branch calls or run via
  Hyperautomation (which may not have the limit; not yet tested).
- **Response is capped at 1000 rows.** For large reads, fetch the raw JSON
  config file via `POST /api/getFile` (path `/datatables/<name>`) with the
  Config Read key — no row cap.
- **`savelookup` modes**: only `'replace'` and `'merge'` parse; both fully
  **overwrite** the entire datatable on each call (no key-based upsert on
  this tenant). To merge multiple feature streams into one table, aggregate
  in Python and write the whole payload via `/api/putFile`. The third
  documented mode `'columns'` parses but its semantics are unclear; key= /
  columns= kwargs error with "Expected a name".

## Functions / syntax

- **String concatenation**: there is no `strcat`/`concat`/`string_concat` —
  the documented way is `format(fmt, ...)`, e.g.
  `let msg = format("%s|%s", role, hospital)`. `+` on strings works in some
  contexts but `format()` is the safe primitive. `||` on strings is parsed
  as boolean OR and times out scans.
- **`let X = (subquery)` for subquery aliasing is NOT supported.** `let` is
  a *pipeline column-derivation command* (`| let col = expr`), not a way
  to alias a reusable query. Every union/join subquery must be self-contained
  — the base pipeline must be repeated inline in each branch.
- **`union` supports at most 10 subqueries.** For ≥11 branches, nest unions.
- **Equality in filters uses `=`, not `==`.**
- **`extend` does NOT exist** — use `| let col = expr` (comma-separated).
- **`if(cond, a, b)` is NOT supported** — use ternary `cond ? a : b`.
- **`case(...)` is NOT supported** — chain ternaries.
- **`isnotnull(x)` is NOT supported** — use `x = *`.
- **Top-level `union` must start with a pipe** (`| union ...`). Bare `union`
  errors with "Don't understand [|]" or "Expected a name".
- **Top-level `dataset` must start with a pipe**:
  `| dataset 'config://datatables/X'` returns the structured table with the
  real column schema. Without the leading pipe, the same string is
  interpreted as a log-search dataset reference and returns
  `[timestamp, message]` log rows.
- **Hour bucket**: `timebucket('1 hour')` in `group ... by`. `bin(ts, 1h)`
  is **not** supported.
- **Conditional count**: `count(condition)`. `countif(...)` 500s.
- **Conditional sum** with `if(...)`: 500s. Pre-aggregate or split into
  another metric.
- **JSON extraction**: parse `message` with regex —
  `| parse '"username": "$user{regex=[^"]+}$"' from message`. Numeric:
  `'"n": $n{regex=[0-9]+}$'`. `parse_jsonpath` is **not** supported.
  `json_object_value` works alone but **500s** with `timebucket` in a group.

## Pipeline structure

- **`parse` FIRST, then `group`.** Inserting filter/let between silently
  drops rows.
- **`dcount(parsed_field)` 500s** post-group. Compute distinct counts via
  a 2-stage `group by entity, field` → `group by entity | count()`.

## Filtering after `group`

- **Null filter**: `| filter <col> = *` (the only working "not null").
- **String empty filter**: `| filter col != ""`.
- **`strlen(col)` is not supported**.

## What works (verified end-to-end)

```powerquery
class_uid = 3002
| parse '"username": "$entity_id{regex=[^"]+}$"' from message
| parse '"outcome": "$outcome{regex=[^"]+}$"' from message
| parse '"event_type": "$event_type{regex=[^"]+}$"' from message
| group
    total = count(),
    fails = count( outcome = "failure" )
  by hour_ts = timebucket('1 hour'), entity_id
| filter entity_id = *
| let fail_ratio = total > 0 ? (1.0 * fails / total) : 0.0
| columns entity_id, hour_ts, total, fails, fail_ratio
| savelookup 'ueba_features_hourly', 'merge'
```

And to read it back:

```powerquery
| dataset 'config://datatables/ueba_features_hourly'
| group rows = count() by feature_name
| sort -rows
```

## Recommended persistence pattern (production)

For multi-feature extractor files that exceed the 15K query limit AND need
multiple feature streams in one table:

1. **Author** each file as `| union (branch1), (branch2), ... | <tail>` for
   human readability and Event Search debugging.
2. **Run via `run_pq_combined.py`** which splits each leaf branch into its
   own API call (READ only), aggregates rows in Python, and writes the
   combined payload via `/api/putFile` (Config Write key). This sidesteps
   both the 15K char limit and savelookup's overwrite semantics.
3. **Scoring/risk/alerts** (files 09–11) are produced by
   `run_ueba_pipeline.py` which reads the populated datatables via
   `/api/getFile`, does z-scores / percentiles / decay in Python, and
   writes outputs via `/api/putFile`.
