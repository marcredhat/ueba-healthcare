# Marc Datatables (one-time setup)

Create these as SDL datatables. Field types are guidance; adjust to your tenant.

## ueba_features_hourly
- entity_type   (string)
- entity_id     (string)
- hour_ts       (timestamp)
- family        (string)  # auth | endpoint | network | cloud | web | dns | file
- feature_name  (string)
- value         (double)

TTL: 35 days.

## ueba_baselines_entity
- entity_type   (string)
- entity_id     (string)
- feature_name  (string)
- mu            (double)
- sigma         (double)
- median        (double)
- q90           (double)
- q99           (double)
- n             (long)
- updated_at    (timestamp)

Refresh mode: replace nightly.

## ueba_baselines_peer
- peer_id       (string)
- feature_name  (string)
- mu            (double)
- sigma         (double)
- median        (double)
- q90           (double)
- q99           (double)
- n             (long)
- updated_at    (timestamp)

Refresh mode: replace nightly.

## ueba_peer_membership
- entity_type   (string)
- entity_id     (string)
- peer_id       (string)
- valid_from    (timestamp)
- valid_to      (timestamp)

Refresh mode: replace weekly (dynamic peers).

## ueba_entity_risk
- entity_type   (string)
- entity_id     (string)
- date          (date)
- score         (double)
- top_features  (string)  # JSON list

Refresh mode: append daily; one row per (entity, date).

## ueba_alerts
- alert_id      (string)
- created_at    (timestamp)
- entity_type   (string)
- entity_id     (string)
- family        (string)
- severity      (string)  # info | low | medium | high | critical
- score         (double)
- explanation   (string)  # JSON: top features, baselines, peer dev
- status        (string)  # new | in_progress | closed | fp | tp

## ueba_watchlist
- entity_type   (string)
- entity_id     (string)
- reason        (string)
- weight        (double)  # multiplier, e.g. 1.5
- valid_from    (timestamp)
- valid_to      (timestamp)

## ueba_service_accounts
- entity_type   (string)
- entity_id     (string)
- type          (string)  # svc | scanner | automation
- owner         (string)
