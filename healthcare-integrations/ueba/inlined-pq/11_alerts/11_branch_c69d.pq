// Auto-generated from 11_alerts.pq
// Feature: branch_c69d
// Writes to: ueba_features_hourly

| dataset 'config://datatables/ueba_family_scores_hourly'
      | filter hour_ts >= now() - 2h
      | filter family_score > 90
      | columns
          alert_id    = format("fam-%s-%s-%s-%s",
                               hour_ts, entity_type, entity_id, family),
          created_at  = now(),
          entity_type,
          entity_id,
          family,
          severity    = family_score > 98 ? "critical"
                      : family_score > 95 ? "high"
                      : "medium",
          score       = family_score,
          explanation = format(
              "family_score=%.2f (>90) at hour_ts=%s",
              family_score, hour_ts),
          status      = "new"
| columns
    alert_id, created_at, entity_type, entity_id, family,
    severity, score, explanation, status
