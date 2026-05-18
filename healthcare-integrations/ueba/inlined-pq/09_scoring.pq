// 09_scoring.pq
// Hourly anomaly scoring.
//
//   z_self        = (value - mu)        / sigma         (entity baseline)
//   z_peer        = (value - mu_peer)   / sigma_peer    (peer baseline)
//   over_q99      = 1 if value > q99   else 0
//   over_q99_peer = 1 if value > q99_p else 0
//   feature_score = max(|z_self|, |z_peer|) + 1.5*over_q99 + 1.5*over_q99_peer
//
// Multi-input join layout: the SDL join requires every named input to
// produce the join-key columns. base_p does not have entity_id (it keys
// on peer_id), so we PRE-JOIN peers + base_p into a single named input
// `peer_baselines` that exposes entity_id, and then do the main 3-way
// join on (entity_type, entity_id, feature_name).
//
// Output schema (matches /datatables/ueba_feature_scores_hourly):
//   entity_type, entity_id, hour_ts, family, feature_name,
//   value, z_self, z_peer, over_q99, over_q99_peer, feature_score
//
| inner join
    feats = (
      | dataset 'config://datatables/ueba_features_hourly'
      | filter hour_ts >= now() - 2h
      | columns entity_type, entity_id, hour_ts, family, feature_name, value
    ),
    base_e = (
      | dataset 'config://datatables/ueba_baselines_entity'
      | columns entity_type, entity_id, feature_name,
                mu, sigma, q99
    ),
    peer_baselines = (
      | inner join
          peers = (
            | dataset 'config://datatables/ueba_peer_membership'
            | columns entity_type, entity_id, peer_id
          ),
          base_p = (
            | dataset 'config://datatables/ueba_baselines_peer'
            | columns entity_type, peer_id, feature_name,
                      mu_peer = mu, sigma_peer = sigma, q99_peer = q99
          )
        on entity_type, peer_id
      | columns entity_type, entity_id, feature_name,
                mu_peer, sigma_peer, q99_peer
    )
  on entity_type, entity_id, feature_name
| let z_self        = sigma      > 0 ? (value - mu)      / sigma      : 0.0
| let z_peer        = sigma_peer > 0 ? (value - mu_peer) / sigma_peer : 0.0
| let over_q99      = (q99      > 0 AND value > q99)      ? 1 : 0
| let over_q99_peer = (q99_peer > 0 AND value > q99_peer) ? 1 : 0
| let feature_score =
        (abs(z_self) > abs(z_peer) ? abs(z_self) : abs(z_peer))
      + 1.5 * over_q99
      + 1.5 * over_q99_peer
| columns
    entity_type, entity_id, hour_ts, family, feature_name,
    value, z_self, z_peer, over_q99, over_q99_peer, feature_score
