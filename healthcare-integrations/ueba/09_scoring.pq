// 09_scoring.pq
// Hourly anomaly scoring.
// Combines self z-score, peer z-score, quantile breaches, watchlist multiplier.
// Outputs per-(entity, hour, family) family_score and feature contributions.

let features  = datatable("ueba_features_hourly")
                | filter hour_ts >= now() - 2h;     // last 2 hours, idempotent re-runs
let base_e    = datatable("ueba_baselines_entity");
let base_p    = datatable("ueba_baselines_peer");
let peers     = datatable("ueba_peer_membership");
let watch     = datatable("ueba_watchlist")
                | filter coalesce(valid_to, now() + 365d) >= now();
let svc       = datatable("ueba_service_accounts");

let scored =
  features
  | join kind=leftouter base_e on entity_type, entity_id, feature_name
  | rename mu=mu, sigma=sigma, q99=q99
  | join kind=leftouter peers on entity_type, entity_id
  | join kind=leftouter base_p on peer_id, feature_name
  | rename mu_peer=mu1, sigma_peer=sigma1, q99_peer=q99_1
  | extend
      z_self        = if(coalesce(sigma, 0.0) > 0, (value - mu) / sigma, 0.0),
      z_peer        = if(coalesce(sigma_peer, 0.0) > 0, (value - mu_peer) / sigma_peer, 0.0),
      over_q99      = if(coalesce(q99, -1.0) >= 0 and value > q99, 1.0, 0.0),
      over_q99_peer = if(coalesce(q99_peer, -1.0) >= 0 and value > q99_peer, 1.0, 0.0)
  | extend
      // robust feature score (0..~10 typical)
      feature_score =
          max_of(abs(z_self), abs(z_peer)) +
          1.5 * over_q99 +
          1.5 * over_q99_peer
  // Suppress service accounts unless extreme
  | join kind=leftouter svc on entity_type, entity_id
  | extend feature_score = if(isnotnull(type) and feature_score < 6.0, 0.0, feature_score)
  // Watchlist multiplier
  | join kind=leftouter watch on entity_type, entity_id
  | extend feature_score = feature_score * coalesce(weight, 1.0)
  | project entity_type, entity_id, hour_ts, family, feature_name,
            value, mu, sigma, q99, mu_peer, sigma_peer, q99_peer,
            z_self, z_peer, over_q99, over_q99_peer, feature_score, peer_id;

// Family score: high quantile of feature scores within the family
let family_scores =
  scored
  | group entity_type, entity_id, hour_ts, family by
      family_score = percentile(feature_score, 95),
      top_features = make_list(
          pack_dict(
              "feature", feature_name,
              "value", value,
              "z_self", z_self,
              "z_peer", z_peer,
              "self_mu", mu, "self_sigma", sigma, "self_q99", q99,
              "peer_mu", mu_peer, "peer_sigma", sigma_peer, "peer_q99", q99_peer,
              "feature_score", feature_score
          ), 5);

// Normalize to 0..100 (cap)
family_scores
| extend family_score_100 = min_of(100.0, family_score * 10.0)
| project entity_type, entity_id, hour_ts, family,
          family_score = family_score_100, top_features
| writeto datatable("ueba_family_scores_hourly", mode="append")
