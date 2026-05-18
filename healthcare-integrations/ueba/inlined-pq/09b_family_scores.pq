// 09b_family_scores.pq
// Rolls per-feature scores up to a family-level score per (entity, hour, family).
// family_score = min(100, p95(feature_score) * 10)
//
// Reads from /datatables/ueba_feature_scores_hourly (produced by 09_scoring.pq).
//
// Output schema (matches /datatables/ueba_family_scores_hourly):
//   entity_type, entity_id, hour_ts, family, family_score, n_features
//
| dataset 'config://datatables/ueba_feature_scores_hourly'
| filter hour_ts >= now() - 2h
| group
    p95_score  = p95(feature_score),
    n_features = count()
  by entity_type, entity_id, hour_ts, family
| let raw_family_score = p95_score * 10.0
| let family_score     = raw_family_score > 100.0 ? 100.0 : raw_family_score
| columns
    entity_type, entity_id, hour_ts, family,
    family_score, n_features
