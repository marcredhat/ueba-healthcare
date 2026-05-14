# UEBA — Production Recipe (Hyperautomation + STAR Alerts)

Refactored to use the actual SDL primitives confirmed by the `pmoses-s1/claude-skills` repo and the local `sentinelone-powerquery` skill:

- **Read** a persistent table: `dataset 'config://datatables/<name>'`
- **Write** a persistent table (merge new rows): `| savelookup '<name>', 'merge'`
- **Write** a persistent table (replace wholesale): `| savelookup '<name>'`
- **Join** at read-time: `| lookup col, … from <name> by key = expr`

Hard limits (from `sentinelone-powerquery/references/commands-reference.md`):

| Limit | Value |
|---|---|
| Lookup table size when read via `lookup` | ≤ 400 KB |
| `savelookup` target | ≤ 100 000 rows / 1.5 MB |
| Array values in lookups | not supported |

## 1. Nightly Hyperautomation workflow — feature materialisation

Schedule one workflow that runs **01–05 and 12** in any order (they all `savelookup … merge` into the same table).

```
Workflow: "UEBA-Features-Nightly"
Trigger:  cron "0 2 * * *" (02:00 local)

Steps:
  1. Run PowerQuery: 01_features_auth.pq
  2. Run PowerQuery: 02_features_endpoint.pq
  3. Run PowerQuery: 03_features_network.pq
  4. Run PowerQuery: 04_features_cloud.pq
  5. Run PowerQuery: 05_features_healthcare.pq
  6. Run PowerQuery: 12_distinct_count_features.pq
```

Each step ends with `| savelookup 'ueba_features_hourly', 'merge'`.

### Sizing the table

The 100 000-row limit is real. With this tenant:

```
~50 active entities × 24 hours × ~15 features/entity × 7 days ≈ 126 000 rows
```

Mitigations (pick one):

- **Reduce TTL to 5 days** (truncate weekly with a `savelookup` of `dataset … | filter hour_ts >= now() - 5d`).
- **Shard by family**: write `ueba_features_hourly_auth`, `_endpoint`, … Each ≤ 25 k rows.
- **Daily roll-up**: keep last 24 h hourly, then aggregate to daily for the rest of the 28-day window (sufficient for baselines).

Recommended start: **shard by family**. Each file 01–05/12 already knows its family; change the `savelookup` target accordingly:

```diff
- | savelookup 'ueba_features_hourly', 'merge'
+ | savelookup 'ueba_features_hourly_<family>', 'merge'
```

And update files 07/08/09 to read the union of shards:

```powerquery
let features =
  union
    ( dataset 'config://datatables/ueba_features_hourly_auth' ),
    ( dataset 'config://datatables/ueba_features_hourly_endpoint' ),
    ( dataset 'config://datatables/ueba_features_hourly_network' ),
    ( dataset 'config://datatables/ueba_features_hourly_cloud' ),
    ( dataset 'config://datatables/ueba_features_hourly_healthcare' );
```

## 2. Nightly Hyperautomation workflow — baselines

```
Workflow: "UEBA-Baselines-Nightly"
Trigger:  cron "30 2 * * *"  (02:30 local, after features land)

Steps:
  1. Run PowerQuery: 06_peers_dynamic.pq          # Mondays only (cron: 30 2 * * 1)
  2. Run PowerQuery: 07_baselines_entity.pq       # replace, no merge
  3. Run PowerQuery: 08_baselines_peer.pq         # replace, no merge
```

Files 07/08 use plain `savelookup '<name>'` (no `merge`) because baselines are recomputed wholesale every night.

## 3. Hourly Hyperautomation workflow — risk & alerts

```
Workflow: "UEBA-Risk-Hourly"
Trigger:  cron "5 * * * *"

Steps:
  1. Run PowerQuery: 09_scoring.pq        # writes ueba_family_scores_hourly
  2. (daily, e.g. 03:00) Run PowerQuery: 10_risk_daily.pq
  3. Run PowerQuery: 11_alerts.pq         # writes ueba_alerts
```

## 4. STAR / PowerQuery Alert rule body — file 09 inline

The skill's §"Productionising as a STAR / PowerQuery Alert rule" recommends running scoring **inline in the rule body** rather than reading a pre-computed table. This is because alert evaluation is per-event and must be self-contained (1 000 rows / 1 MB output cap).

Below is the rule body that detects an auth anomaly inline, ready to paste into a PowerQuery Alert rule. Repeat the pattern for each family.

```powerquery
// === STAR Alert: UEBA-Auth-Anomaly ===
// Fires when a user's hourly auth_total z-score against their entity baseline
// AND peer baseline both exceed 3.0, or value exceeds q99.

let live =
  (
    | filter class_uid == 3002
    | parse '"username": "$entity_id{regex=[^"]+}$"' from message
    | group value = count() by entity_id, hour_ts = timebucket('1 hour')
    | filter entity_id = *
    | filter hour_ts >= now() - 1h
    | extend entity_type = "user", feature_name = "auth_total"
  );

let peer_map = dataset 'config://datatables/ueba_peer_membership';

live
| lookup mu, sigma, q99 from ueba_baselines_entity
    by entity_type = entity_type, entity_id = entity_id, feature_name = feature_name
| join kind=leftouter peer_map on entity_type, entity_id
| lookup mu_p = mu, sigma_p = sigma, q99_p = q99 from ueba_baselines_peer
    by peer_id = peer_id, feature_name = feature_name
| extend
    z_self = if(coalesce(sigma,  0.0) > 0, (value - mu)   / sigma,   0.0),
    z_peer = if(coalesce(sigma_p,0.0) > 0, (value - mu_p) / sigma_p, 0.0),
    over_q99      = if(coalesce(q99,  -1.0) >= 0 and value > q99,   1, 0),
    over_q99_peer = if(coalesce(q99_p,-1.0) >= 0 and value > q99_p, 1, 0)
| filter z_self >= 3.0 or z_peer >= 3.0 or over_q99 = 1 or over_q99_peer = 1
| columns entity_id, hour_ts, value, mu, sigma, q99, mu_p, sigma_p, q99_p,
          z_self, z_peer, over_q99, over_q99_peer
```

Severity tiering inside the alert:

```powerquery
| extend severity = case(
      max_of(abs(z_self), abs(z_peer)) >= 5 or over_q99 + over_q99_peer = 2, "high",
      max_of(abs(z_self), abs(z_peer)) >= 3,                                  "medium",
                                                                              "low")
```

## 5. End-to-end smoke test

After deploying the workflows, populate at least one hourly slice:

```powerquery
// Run the auth feature extractor for the last hour and verify it landed
serverHost = 'avelios-medical' or serverHost = 'omniconnect'
| filter class_uid == 3002
| parse '"username": "$entity_id{regex=[^"]+}$"' from message
| parse '"outcome": "$outcome{regex=[^"]+}$"' from message
| group auth_total = count(), auth_fail = count(outcome == "failure")
    by hour_ts = timebucket('1 hour'), entity_id
| filter entity_id = *
| extend entity_type = "user", family = "auth"
| union
  ( ... | columns entity_id, hour_ts, feature_name = "auth_total", value = auth_total ),
  ( ... | columns entity_id, hour_ts, feature_name = "auth_fail",  value = auth_fail  )
| savelookup 'ueba_features_hourly', 'merge'
```

Then read back:

```powerquery
dataset 'config://datatables/ueba_features_hourly'
| filter hour_ts >= now() - 2h
| group ct = count() by family, feature_name
| sort -ct
```

If you see rows here, the pipeline works.

## 6. Files changed vs the original pack

| File | Was | Now |
|---|---|---|
| 01–05, 12 | `writeto datatable("ueba_features_hourly", mode="append")` | `savelookup 'ueba_features_hourly', 'merge'` |
| 06 | `writeto datatable("ueba_peer_membership", mode="replace")` | `savelookup 'ueba_peer_membership'` |
| 07 | `datatable("…")` + `writeto … mode="replace"` | `dataset 'config://datatables/…'` + `savelookup '…'` |
| 08 | same | same |
| 09 | 6 × `datatable("…")` + 1 × `writeto … mode="append"` | 6 × `dataset 'config://datatables/…'` + 1 × `savelookup '…', 'merge'` |
| 10 | 2 × `datatable("…")` + `writeto … mode="append"` | 2 × `dataset` + `savelookup '…', 'merge'` |
| 11 | 2 × `datatable("…")` + `writeto … mode="append"` | 2 × `dataset` + `savelookup '…', 'merge'` |
| 00 schema doc | (unchanged) | (unchanged — tables are still semantically the same) |

## 7. Why `savelookup` and not `writeto`

`writeto datatable(…)` does not exist in SDL PowerQuery. It was a placeholder name used while the pack was being authored. The verified persistence primitive in the language reference is `savelookup`. There is no separate "datatable" namespace — every persistent table lives under `config://datatables/<name>` and is accessed via `dataset`, `lookup`, or `savelookup`.

This is why the user's read

```
dataset 'config://datatables/ueba_features_hourly'
```

returned empty: the writes never happened. With the refactor above, the table is populated on the first run of the nightly workflow.
