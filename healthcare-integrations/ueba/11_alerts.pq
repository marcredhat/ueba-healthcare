// 11_alerts.pq
// Generate UEBA alerts from two triggers:
//   (a) family_score > 90   (hourly, per entity × family)
//   (b) daily_risk   > 70   (per entity per day)
//
// Output schema (matches /datatables/ueba_alerts):
//   alert_id, created_at, entity_type, entity_id, family,
//   severity, score, explanation, status
//
| union
    (
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
    ),
    (
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
    )
| columns
    alert_id, created_at, entity_type, entity_id, family,
    severity, score, explanation, status
