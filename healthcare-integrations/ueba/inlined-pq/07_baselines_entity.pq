// 07_baselines_entity.pq
// Nightly per-entity baselines over the last 28 days.
// Requires >= 14 days of hourly samples per feature to be considered stable.
//
// Output schema (matches /datatables/ueba_baselines_entity):
//   entity_type, entity_id, feature_name, mu, sigma, median, q90, q99, n, updated_at
//
| dataset 'config://datatables/ueba_features_hourly'
| filter hour_ts >= now() - 29d
| filter hour_ts <  now() - 1d
| group
    mu     = avg(value),
    sigma  = stddev(value),
    median = p50(value),
    q90    = p90(value),
    q99    = p99(value),
    n      = count()
  by entity_type, entity_id, family, feature_name
| filter n >= 336        // ~14 days × 24 hourly samples
| columns
    entity_type, entity_id, family, feature_name,
    mu, sigma, median, q90, q99, n,
    updated_at = now()
