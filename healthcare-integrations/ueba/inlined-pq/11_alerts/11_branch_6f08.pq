// Auto-generated from 11_alerts.pq
// Feature: branch_6f08
// Writes to: ueba_features_hourly

| dataset 'config://datatables/ueba_entity_risk'
      | filter date >= now() - 1d
      | filter score > 70
      | columns
          alert_id    = format("risk-%s-%s-%s", date, entity_type, entity_id),
          created_at  = now(),
          entity_type,
          entity_id,
          family      = "risk",
          severity    = score > 90 ? "critical"
                      : score > 80 ? "high"
                      : "medium",
          score,
          explanation = format("daily_risk=%.2f (>70) for date=%s", score, date),
          status      = "new"
| columns
    alert_id, created_at, entity_type, entity_id, family,
    severity, score, explanation, status
