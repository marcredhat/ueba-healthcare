// 11_alerts.pq
// Generate UEBA alerts with explanations.
// Two triggers:
//   (a) Family score > 90 (per hour)
//   (b) Daily entity risk > 70
// Each alert includes top contributing features as JSON.

let today_d = bin(now(), 1d);

// (a) Family-level hourly anomalies
let family_alerts =
  dataset 'config://datatables/ueba_family_scores_hourly'
  | filter hour_ts >= now() - 2h
  | filter family_score > 90
  | extend
      alert_id    = strcat("fam-", tostring(hour_ts), "-", entity_type, "-", entity_id, "-", family),
      created_at  = now(),
      severity    = case(family_score > 98, "critical",
                         family_score > 95, "high",
                         "medium"),
      explanation = tostring(pack_dict(
                       "trigger",      "family_score",
                       "family",       family,
                       "hour_ts",      hour_ts,
                       "family_score", family_score,
                       "top_features", top_features
                   )),
      status      = "new"
  | project alert_id, created_at, entity_type, entity_id, family, severity,
            score = family_score, explanation, status;

// (b) Entity-level daily risk
let risk_alerts =
  dataset 'config://datatables/ueba_entity_risk'
  | filter date == today_d and score > 70
  | extend
      alert_id    = strcat("risk-", tostring(date), "-", entity_type, "-", entity_id),
      created_at  = now(),
      family      = "risk",
      severity    = case(score > 90, "critical",
                         score > 80, "high",
                         "medium"),
      explanation = tostring(pack_dict(
                       "trigger", "daily_risk",
                       "date",    date,
                       "score",   score
                   )),
      status      = "new"
  | project alert_id, created_at, entity_type, entity_id, family, severity,
            score, explanation, status;

union family_alerts, risk_alerts
| savelookup 'ueba_alerts', 'merge'
