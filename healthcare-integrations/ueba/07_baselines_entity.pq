// 07_baselines_entity.pq
// Nightly per-entity baselines over the last 28 days.
// Requires >= 14 days of hourly samples per feature to be considered stable.

dataset 'config://datatables/ueba_features_hourly'
| filter hour_ts between (now() - 29d) and (now() - 1d)
| group entity_type, entity_id, feature_name by
    mu     = avg(value),
    sigma  = stddev(value),
    median = percentile(value, 50),
    q90    = percentile(value, 90),
    q99    = percentile(value, 99),
    n      = count()
| filter n >= 24 * 14  // ~14 days of hourly samples
| extend updated_at = now()
| project entity_type, entity_id, feature_name,
          mu, sigma, median, q90, q99, n, updated_at
| savelookup 'ueba_baselines_entity'
