# UEBA Healthcare — Runnable PowerQuery files

Inlined, self-contained PowerQuery (.pq) files derived from
https://github.com/marcredhat/ueba-healthcare. Every `let X = ( ... )`
definition has been pasted inline because the SDL parser on the target
tenant rejects `let X = (subquery)` aliasing.

For files that produced more than one feature via a single `| union`
(01–05, 12), the source has been **split into one .pq per feature** so
that each file stays under the 15,000-character `/api/powerQuery`
request-body limit.

## Layout

```
01_features_auth/
    01_auth_total.pq
    01_auth_fail.pq
    ...
02_features_endpoint/
    ...
06_peers_dynamic.pq           # single-query files stay flat
07_baselines_entity.pq
08_baselines_peer.pq
09_scoring.pq
09b_family_scores.pq
10_risk_daily.pq
11_alerts.pq
```

## Running one file

```bash
QUERY=$(cat 01_features_auth/01_auth_total.pq)
curl -X POST "$SDL_URL/api/powerQuery"                  \
     -H "Authorization: Bearer $SDL_LOG_READ_KEY"        \
     -H "Content-Type: application/json"                 \
     -d "{\"query\":\"$QUERY\",\"startTime\":\"24h\"}"
```

Or paste any file into the AI SIEM PowerQuery UI.

## Pipeline order

1. 01–05, 12 (features → `ueba_features_hourly`)
2. 06 (peers → `ueba_peer_membership`)
3. 07 (entity baselines → `ueba_baselines_entity`)
4. 08 (peer baselines → `ueba_baselines_peer`)
5. 09 (scoring → `ueba_feature_scores_hourly`)
6. 09b (family rollup → `ueba_family_scores_hourly`)
7. 10 (daily risk → `ueba_entity_risk`)
8. 11 (alerts → `ueba_alerts`)
