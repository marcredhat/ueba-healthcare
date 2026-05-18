// 08_baselines_peer.pq
// Nightly per-peer baselines over the last 28 days.
// Joins ueba_features_hourly with current ueba_peer_membership using
// named join inputs (the closest thing to SQL subquery aliasing in
// SDL PowerQuery).
//
// Output schema (matches /datatables/ueba_baselines_peer):
//   entity_type, peer_id, feature_name, mu, sigma, median, q90, q99, n, updated_at
//
| inner join
    feats = (
      | dataset 'config://datatables/ueba_features_hourly'
      | filter hour_ts >= now() - 29d
      | filter hour_ts <  now() - 1d
      | columns entity_type, entity_id, family, feature_name, value
    ),
    peers = (
      | dataset 'config://datatables/ueba_peer_membership'
      | columns entity_type, entity_id, peer_id
    )
  on entity_type, entity_id
| group
    mu     = avg(value),
    sigma  = stddev(value),
    median = p50(value),
    q90    = p90(value),
    q99    = p99(value),
    n      = count()
  by entity_type, peer_id, family, feature_name
| filter n >= 336        // ~14 days × 24 samples
| columns
    entity_type, peer_id, family, feature_name,
    mu, sigma, median, q90, q99, n,
    updated_at = now()
