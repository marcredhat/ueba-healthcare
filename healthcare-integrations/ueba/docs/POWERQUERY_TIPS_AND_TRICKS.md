# SentinelOne SDL PowerQuery — tips, tricks, and verified best practices

Practical lessons learned building this UEBA pipeline against
`<your-tenant>.sentinelone.net`. Every entry below is **empirically
verified**: each rule was confirmed by submitting test queries against
`/api/powerQuery` and observing the parser's response. The pipeline at
``
follows every rule documented here and 90/90 inlined files
parse-and-execute successfully on the tenant.

This document is intended for any analyst, engineer, or AI agent
writing PowerQuery against the SentinelOne Singularity Data Lake.

---

## 1. Choose the canonical operator forms — variants may "work" until they don't

The parser accepts a number of syntactic synonyms (`==` vs `=`, `&&`
vs `AND`, etc.) but only one form is **canonical** and reliably
documented. Use these forms; reviewers and downstream tools assume
them.

| Canonical | Avoid | Reason |
|---|---|---|
| `=` (equality) | `==` | Documented synonym only |
| `AND` / `OR` | `&&` / `\|\|` | Some places (literal regexes, embedded JSON) trip the `\|\|` parser |
| `count(condition)` | `countif(condition)` | `countif` is not a recognized function on this tenant |
| `p50(x)`, `p90(x)`, `p95(x)`, `p99(x)` | `percentile(x, 95)` | `percentile(...)` returns `Don't understand` error |
| `timebucket('1 hour')` | `bin(timestamp, 1h)` | `bin()` is from a different dialect; not recognized |
| `timebucket(<field>, '1 day')` | `timebucket('1 day')` then hoping it bucketed the right column | Explicit form is unambiguous when the implicit `_time` isn't what you want |
| `filter <col> = *` | `filter isnotnull(<col>)` | `isnotnull` is not a function; `= *` is the documented null-existence test |

**Rule**: when in doubt, prefer the form documented in the
official scalyr / SDL PowerQuery reference. Synonyms exist but are
not future-proof.

---

## 2. `let X = (subquery)` aliasing is NOT supported

Most SQL-like languages let you name a subquery and reference it
multiple times. PowerQuery in this tenant **does not**:

```
let base = (
  | filter class_uid = 3002
  | parse ... from message
  | group n = count() by entity_id, hour_ts = timebucket('1 hour')
);
| union
  ( base | columns entity_id, feature = "auth_total", value = n ),
  ( base | columns entity_id, feature = "auth_succ",  value = n )
```

submitted to `/api/powerQuery` returns:

```
HTTP 400  invalid query: Don't understand [|] -- try enclosing it in quotes
```

The parser rejects the leading `|` inside the parens **and** rejects
the bare-expression form without the pipe.

**Workaround**: inline the base pipeline into each branch by hand (or
by a build script). See the `_expand_let_base` function in
`build_inlined_pq.py`
for the automated transform. The source `.pq` files use the concise
`let base = (...)` for readability; the build step emits inlined
runnable copies into `inlined-pq/`.

---

## 3. Named-input joins are the closest thing to subquery aliasing

Where `let X = (...)` would have been useful, **multi-input joins**
fill the gap. The general form:

```
| inner join
    input1 = ( | dataset 'config://...' | columns key, fieldA, fieldB ),
    input2 = ( | dataset 'config://...' | columns key, fieldC )
  on key
| ... downstream operations referencing fieldA, fieldB, fieldC ...
```

Key rules learned:

### 3.1 Join keys go in a comma-separated list, not as boolean equality
```
on entity_type, entity_id, feature_name        // correct
on entity_type = entity_type AND entity_id = entity_id   // ERROR
```

### 3.2 Every named input MUST produce every key listed in `on ...`
If `base_p` doesn't have `entity_id` (it keys on `peer_id` instead), a
4-way join on `(entity_type, entity_id, feature_name)` returns:

```
HTTP 400  Join field 'entity_id' was not found in all subqueries
```

**Fix**: pre-join the table that's missing a key with a lookup table
that has it, then use the result as a single named input. Example
from
`09_scoring.pq`:

```
peer_baselines = (
  | inner join
      peers  = ( | dataset 'config://...' | columns entity_type, entity_id, peer_id ),
      base_p = ( | dataset 'config://...' | columns entity_type, peer_id, feature_name, mu_peer, ... )
    on entity_type, peer_id
  | columns entity_type, entity_id, feature_name, mu_peer, ...
)
```

`peer_baselines` now exposes `entity_id` (via the `peers` mapping) and
can participate in the outer join on `(entity_type, entity_id,
feature_name)`. **Joins nest cleanly**.

### 3.3 Specify the join kind explicitly
```
| inner join ...      // correct
| outer join ...      // correct
| left join ...       // correct
| join ...            // works but ambiguous
| join kind=inner ... // ERROR: kind= is not a recognized syntax
```

### 3.4 After a join, ambiguous field names MUST be qualified
If both join inputs output a field named `day`, the parser rejects an
unqualified reference:

```
HTTP 400  undefined field 'day'
```

**Fix**: reference as `<input_name>.day`. From
`10_risk_daily.pq`:

```
| let date = today.day = null ? yday.day : today.day
```

Use the input name (not the dataset name) — it's whatever you wrote
to the left of the `=` in the named-input list.

---

## 4. `| let` cannot redefine an existing column

```
| group today_sum = sum(contribution) by entity_id, day
| let today_sum = today_sum = null ? 0 : today_sum    // ERROR
```

Returns:

```
HTTP 400  duplicate definition of field 'today_sum'
```

**Fix**: choose a new name for the derived value.

```
| let today_safe = today_sum = null ? 0 : today_sum
| let score      = today_safe > decayed ? today_safe : decayed
| columns ..., score
```

This forces a clean dataflow: each `| let` introduces a new field; old
fields stay as they were.

---

## 5. Order of operations: parse first, then group; never insert filter between

This is the single most common cause of mysterious "field not found"
errors:

```
| filter class_uid = 3002
| parse '"username": "$user{regex=[^"]+}$"' from message
| parse '"event_type": "$etype{regex=[^"]+}$"' from message
| group n = count(etype = "USER_LOGIN_SUCCESS") by hour_ts = timebucket('1 hour'), user
| filter user = *               // <-- this filter goes AFTER group
```

**Wrong**:

```
| parse '"username": "$user{regex=[^"]+}$"' from message
| filter user = *                            // breaks
| parse '"event_type": "$etype{regex=[^"]+}$"' from message
```

Inserting a filter between parses or before group can cause the
downstream `parse` results to be invisible. Always: filter → parse(s)
→ group → post-group filters.

---

## 6. `dcount` on parse-extracted fields returns HTTP 500 — use a two-stage group

This is undocumented but consistent on this tenant:

```
| parse '"event_type": "$v{regex=[^"]+}$"' from message
| group n = dcount(v) by entity_id, hour_ts = timebucket('1 hour')

→ HTTP 500
```

**Fix** — collapse-then-count pattern:

```
| parse '"event_type": "$v{regex=[^"]+}$"' from message
| group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
| filter entity_id = *
| filter v = *
| group value = count() by hour_ts, entity_id
```

The inner `group` deduplicates the (entity_id, hour_ts, v) tuples, and
the outer `group` counts the remaining distinct rows. The output is
identical to a `dcount(v)` but doesn't trip the 500.

See every feature in
`12_distinct_count_features.pq`.

---

## 7. `sum(if(cond, x, 0))` inside `group` returns HTTP 500

Another undocumented limitation:

```
| group total = sum(if(outcome = "failure", 1, 0)) by entity_id

→ HTTP 500
```

**Fix**: use `count(condition)`, which is the documented form anyway:

```
| group total = count(outcome = "failure") by entity_id
```

For non-counting aggregations of conditional values, use a `| let`
projection before the group:

```
| let weighted = (severity = "high" ? 5 : 1)
| group total = sum(weighted) by entity_id
```

---

## 8. `| filter` on aggregate columns must come AFTER `| group`

This is the canonical post-group filter pattern:

```
| group n = count(), p95 = p95(value) by entity_id, hour_ts = timebucket('1 hour')
| filter entity_id = *           // null check on group-by key
| filter n >= 10                 // numerical condition on aggregate
```

Filtering BEFORE `group` only sees raw event fields; the aggregate
columns don't exist yet.

---

## 9. Use `filter <col> = *` for null existence, not `isnotnull`

```
| filter entity_id = *    // correct
| filter isnotnull(entity_id)   // ERROR — isnotnull is not a function
```

The `= *` form is the documented PowerQuery null-existence test on
this tenant.

---

## 10. Ternary expressions instead of `if(cond, a, b)`

`if(...)` is generally available for non-aggregate use, but ternary is
the cleaner idiom and avoids the `sum(if(...))` group bug entirely:

```
| let weight =
        family = "healthcare" ? 1.5
      : family = "cloud"      ? 1.4
      : family = "endpoint"   ? 1.3
      : 1.0
```

Chained ternaries are the SDL equivalent of `CASE WHEN ... THEN ...
ELSE ... END`.

---

## 11. Null-safe arithmetic with explicit ternary

After an `outer join`, fields from missing right-side rows are `null`.
Arithmetic on `null` propagates `null` and breaks downstream
comparisons. Always defend explicitly:

```
| let today_safe = today_sum  = null ? 0   : today_sum
| let decayed    = yday_score = null ? 0   : yday_score * 0.7071
| let score      = today_safe > decayed ? today_safe : decayed
```

(See rule 4 — `today_safe` must be a new name, you can't reassign
`today_sum`.)

---

## 12. The 15,000-character `/api/powerQuery` body limit

Submitting a query body longer than 15,000 characters returns:

```
HTTP 400  parameter query is 24401 characters long; maximum is 15000
{ "status": "error/client/badParam/tooLarge" }
```

This is **strict**. There is no way around it server-side.

**Implications**:

1. A 15-branch `| union` of 1.7 KB base pipelines totals ~25 KB —
   exceeds the limit
2. Per-branch splitting is the only API-compatible workaround
3. The PowerQuery UI may accept longer queries, but anything you
   schedule, automate, or invoke programmatically must respect 15K

**Workaround**: split a multi-branch source into N independent
single-branch `.pq` files, each writing to the same datatable with
`| savelookup '<name>', 'merge'`. This is what
`build_inlined_pq.py`
does automatically.

---

## 13. Use `savelookup ... 'merge'` for incremental writes to datatables

```
| columns entity_type, entity_id, hour_ts, family, feature_name, value
| savelookup 'ueba_features_hourly', 'merge'
```

Modes:

| Mode | Behavior |
|---|---|
| `'replace'` | Truncate the table and write |
| `'merge'`   | Upsert on the table's primary key |
| `'append'`  | Add rows without deduplication |

For UEBA feature tables, **`'merge'`** is correct: re-running the
hour-N pipeline overwrites stale hour-N rows without affecting other
hours.

---

## 14. Read from configured datatables with `| dataset 'config://...'`

```
| dataset 'config://datatables/ueba_features_hourly'
| filter hour_ts >= now() - 2h
| columns entity_type, entity_id, family, feature_name, value
```

The `config://` URI scheme is the canonical form for reading from a
declared datatable. The string after `datatables/` must match the
datatable name exactly (case-sensitive). Look up available names with
the SDL `GET /api/dataDictionary/datatables` endpoint.

---

## 15. Bucketed time aggregation patterns

| Goal | Pattern |
|---|---|
| Hourly buckets of `_time` (implicit) | `by hour_ts = timebucket('1 hour')` |
| Daily buckets of `_time` | `by day = timebucket('1 day')` |
| Daily buckets of a specific field | `by day = timebucket(hour_ts, '1 day')` |
| Filter "current day" | `| filter date >= timebucket(now(), '1 day')` |
| Filter "previous day" | `| filter date >= timebucket(now(), '1 day') - 1d \| filter date < timebucket(now(), '1 day')` |

The explicit-field form `timebucket(<field>, ...)` is essential
whenever a pipeline produces an intermediate timestamp field
(`hour_ts`, `date`) and you want to bucket that field rather than the
implicit `_time`.

---

## 16. Parsing JSON-in-message fields

OCSF events often arrive with the full event body in a single
`message` string field. The PowerQuery `parse` command can extract
substrings using named regex captures:

```
| parse '"username": "$entity_id{regex=[^"]+}$"' from message
| parse '"outcome":  "$outcome{regex=[^"]+}$"'   from message
| parse '"event_type": "$event_type{regex=[^"]+}$"' from message
```

Each `parse` consumes the entire `message` field and adds the captured
named groups as new columns. Subsequent parses see the same `message`,
not the result of the previous parse — so you can run as many parses
as you need without worrying about chained substitution.

**Tip**: if a parse fails to match, the captured field will be null
on that row. Use `| filter <col> = *` after the parses to drop rows
that didn't match.

---

## 17. `union` flat-lists branches; nest unions to exceed 10 branches

```
| union
  ( <pipeline 1> ),
  ( <pipeline 2> ),
  ...
  ( <pipeline 10> )
| <tail>
```

The documented limit is **10 union branches** at one level. For 15
features, nest:

```
| union
  ( | union ( b1 ), ( b2 ), ... ( b10 ) ),
  ( | union ( b11 ), ( b12 ), ... ( b15 ) )
| <tail>
```

In our pipeline, this nesting is automated by the build script — the
source files stay flat-listed for readability, and the inliner
respects whatever structure the source uses.

---

## 18. `format(...)` for templated strings in `columns`

For alert text and tooltips:

```
| let alert_text = format(
    "Anomaly on {0} {1} at {2}: score={3} (z_self={4}, z_peer={5})",
    entity_type, entity_id, hour_ts, score, z_self, z_peer
  )
| columns entity_id, hour_ts, alert_text
```

`format()` accepts positional `{0}`, `{1}`, etc. and converts each
argument to its string representation.

---

## 19. Debugging recipe — minimal narrowing

When a query returns an unhelpful HTTP 400 like `Don't understand
[|]`, narrow it:

1. **Remove the savelookup**: replace `| savelookup 'foo'` with
   `| limit 5`. This isolates parser errors from write-permission
   errors.
2. **Comment out trailing pipes**: keep deleting the last pipe step
   until the query parses. The first step that breaks is the
   culprit.
3. **Inline subqueries**: replace `| inner join a = (...)` with the
   raw `(...)` content if you suspect named-input issues.
4. **Check the build artifact**: the inlined version of each source
   `.pq` file lives at
   `inlined-pq/`.
   What you actually submit is what's there, not the concise source.
5. **Submit programmatically with `/api/powerQuery`**: the UI may
   silently rewrite or sanitize. The raw API surfaces the precise
   parser error.

---

## 20. Validation discipline

Every change to a `.pq` source must be followed by:

```
python3 build_inlined_pq.py
python3 validate_all.py
```

The first rebuilds the inlined `.pq` artifacts; the second submits all
90 to the tenant and reports per-file pass/fail. **The pipeline is
considered correct only when `validate_all.py` reports 90/90 PASS**.
Last verified: 2026-05-18, all 90 PASS on `<your-tenant>.sentinelone.net`.

---

## Cheat sheet (one-page reference)

```
operators       =   AND  OR  ?:        // not ==, &&, ||, if()
percentile      p50(x) p90(x) p95(x)   // not percentile(x, 95)
distinct count  two-stage group        // not dcount on parsed fields
conditional sum count(cond)            // not sum(if(cond, 1, 0))
time bucket     timebucket('1 hour')   // also timebucket(field, '1 day')
null existence  field = *              // not isnotnull(field)
join keys       on a, b, c             // not on a = a AND b = b
join kinds      inner|outer|left join  // not kind=inner
join all-keys   every input must produce every key
join ambig.     name.field             // qualify when shared
let redefinition  pick a new name      // duplicate definition error
subquery alias  inline by hand         // let X = (subq) not supported
body size       < 15000 characters     // per-branch split if larger
write           | savelookup 'tbl', 'merge'
read            | dataset 'config://datatables/<name>'
parse           | parse '"k":"$cap{regex=[^"]+}$"' from message
union           ≤ 10 branches / level  // nest if more
```
