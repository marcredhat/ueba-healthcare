// 08_baselines_peer.pq
// Nightly per-peer baselines over the last 28 days.
// Joins ueba_features_hourly with current ueba_peer_membership.

let peers = dataset 'config://datatables/ueba_peer_membership';

dataset 'config://datatables/ueba_features_hourly'
| filter hour_ts between (now() - 29d) && (now() - 1d)
| join kind=inner peers on entity_type, entity_id
| group peer_id, feature_name by
    mu     = avg(value),
    sigma  = stddev(value),
    median = percentile(value, 50),
    q90    = percentile(value, 90),
    q99    = percentile(value, 99),
    n      = count()
| filter n >= 24 * 14
| let updated_at = now()
| project peer_id, feature_name, mu, sigma, median, q90, q99, n, updated_at
| savelookup 'ueba_baselines_peer'
