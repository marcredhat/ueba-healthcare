# UEBA Production Recipe

This document tells you exactly how to populate every UEBA datatable in this
tenant, from raw events to alerts. It supersedes the old plan that assumed
Event-Search-only execution and `savelookup`-as-merge.

## Architecture (verified)

```
                                                          /api/putFile
   raw events (class_uid=3002, 4001, …)                       ▲
            │                                                 │
   01–05 + 12  ─── run_pq_combined.py ───────────►  ueba_features_hourly
   (per-feature READ calls, rows aggregated in Python)        │
                                                              │
   run_ueba_pipeline.py (reads each table via /api/getFile,   │
                         writes via /api/putFile)             ▼
                                          ueba_peer_membership
                                          ueba_baselines_entity
                                          ueba_baselines_peer
                                          ueba_feature_scores_hourly
                                          ueba_family_scores_hourly
                                          ueba_entity_risk
                                          ueba_alerts
```

All writes go through `/api/putFile` because `savelookup` on this tenant
fully **replaces** the table contents on every call (no key-based upsert).
The Python orchestrator collects multi-source rows in memory then writes
the final payload once per datatable.

## Daily / hourly schedule

| Cadence | Step | Command |
|---------|------|---------|
| Hourly  | Pull last hour's features | `python3 ueba/run_pq_combined.py --all --start 1h --table ueba_features_hourly` |
| Hourly  | Score features, update family scores, risk, alerts | `python3 ueba/run_ueba_pipeline.py` |
| Daily   | Rebuild peers (cheap; only 8 users so far) | `python3 ueba/run_ueba_pipeline.py --stage peers` |
| Weekly  | Rebuild full 14-day baselines | `python3 ueba/run_ueba_pipeline.py --stage baselines && python3 ueba/run_ueba_pipeline.py --stage peer_baselines` |

For Hyperautomation deployment: wrap each command in a small Python action
that exits non-zero on `_http` errors, and chain them with `on_success`.

## End-to-end smoke test

```bash
cd ueba

# 1. Verify the API tenant + keys work
python3 _test_query_shapes.py

# 2. Populate features (writes /datatables/ueba_features_hourly)
python3 run_pq_combined.py --all --start 24h

# 3. Build everything downstream
python3 run_ueba_pipeline.py

# 4. Verify
python3 verify_features.py
```

Expected on the seeded synthetic data (24h window, 8 users, 13 hosts):

- `ueba_features_hourly`            ~1,200 rows (15 features × ~80 user-hours)
- `ueba_peer_membership`            ~20 rows
- `ueba_baselines_entity`           ~100 rows
- `ueba_baselines_peer`             ~60 rows
- `ueba_feature_scores_hourly`      ~1,200 rows
- `ueba_family_scores_hourly`       ~80 rows
- `ueba_entity_risk`                ~10–20 rows
- `ueba_alerts`                     0 (thresholds default to 90 / 70; synthetic
                                       data is too uniform to trip them)

To validate the alert path end-to-end, lower the thresholds at the top of
`run_ueba_pipeline.py` (`ALERT_FAMILY_THRESHOLD`, `ALERT_RISK_THRESHOLD`) or
inject a row with a high score via `/api/putFile`.

## Key files

| File | Purpose |
|------|---------|
| `01_features_auth.pq` … `05_features_healthcare.pq`, `12_distinct_count_features.pq` | Feature extractors. Authored as `| union (b1),(b2),… | tail` for readability. Executed branch-by-branch by `run_pq_combined.py`. |
| `06_peers_dynamic.pq` | Legacy reference only. Peer logic now lives in `run_ueba_pipeline.py::stage_peers`. |
| `07_baselines_entity.pq`, `08_baselines_peer.pq` | Legacy reference only. Baseline math is in Python (stable, no SDL quirks). |
| `09_scoring.pq`, `10_risk_daily.pq`, `11_alerts.pq` | Legacy reference only. Implemented in Python — the SDL `join` + `let X = pipeline` chains required here are too tenant-fragile. |
| `run_pq_combined.py` | Run a feature-extractor file: split union, READ each leaf, aggregate, write via putFile. |
| `run_ueba_pipeline.py` | All downstream stages: peers, baselines, scoring, risk, alerts. |
| `verify_features.py` | Sanity-check the populated `ueba_features_hourly` table. |
| `SDL_POWERQUERY_QUIRKS.md` | All the gotchas, with verified examples. |

## STAR / inline alert rule (optional, for tenant-side alerting)

If you'd rather use SDL's native alerting on top of `ueba_alerts`:

```powerquery
| dataset 'config://datatables/ueba_alerts'
| filter created_at >= now() - 1h
| filter severity = "critical" || severity = "high"
| columns alert_id, entity_type, entity_id, family, severity, score, explanation
```

Schedule every 5 minutes, set the alert severity from the row's `severity`
column, and route via the standard SDL alert sinks.

## Caveats

- **savelookup overwrite**: do not point two different writers at the same
  datatable — the second one wipes the first. Always orchestrate from
  Python so the final write is a single atomic putFile.
- **15K query limit**: keep any single `/api/powerQuery` body well under
  15,000 chars. The branch-splitter in `run_pq_combined.py` keeps each
  call ~1,500 chars.
- **1000-row response cap**: `/api/powerQuery` caps reads at 1,000 rows.
  For full datatable reads use `/api/getFile` (already done by
  `run_ueba_pipeline.py::fetch_table`).
- **Health of synthetic data**: alerts will be sparse on the seeded fixture
  until you inject more variance or extend the time window so baselines
  have enough variance to flag a real outlier.
