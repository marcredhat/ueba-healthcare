// 10_risk_daily.pq
// Daily entity risk = weighted sum of per-family p95 scores, with
// exponential decay carried forward from the previous day.
//
//   today_sum(entity)   = SUM_family(weight(family) * p95(family_score))
//   decayed(entity)     = yday_score * 0.7071     // 24h decay, half-life 48h
//   today_score(entity) = max(today_sum, decayed)
//
// Output schema (matches /datatables/ueba_entity_risk):
//   entity_type, entity_id, date, score

| outer join
    today = (
      | dataset 'config://datatables/ueba_family_scores_hourly'
      | filter hour_ts >= timebucket(now(), '1 day')
      | group p95_score = p95(family_score)
        by entity_type, entity_id, family, day = timebucket(hour_ts, '1 day')
      | let weight =
              family = "healthcare" ? 1.5
            : family = "cloud"      ? 1.4
            : family = "endpoint"   ? 1.3
            : family = "auth"       ? 1.0
            : family = "file"       ? 0.9
            : family = "network"    ? 0.8
            : family = "dns"        ? 0.7
            : family = "web"        ? 0.6
            : 1.0
      | let contribution = p95_score * weight
      | group today_sum = sum(contribution)
        by entity_type, entity_id, day
      | columns entity_type, entity_id, day, today_sum
    ),
    yday = (
      | dataset 'config://datatables/ueba_entity_risk'
      | filter date >= timebucket(now(), '1 day') - 1d
      | filter date <  timebucket(now(), '1 day')
      | let day = timebucket(now(), '1 day')
      | columns entity_type, entity_id, day, yday_score = score
    )
  on entity_type, entity_id
| let today_safe = today_sum  = null ? 0 : today_sum
| let decayed    = yday_score = null ? 0 : yday_score * 0.7071
| let score      = today_safe > decayed ? today_safe : decayed
| let date       = today.day  = null ? yday.day : today.day
| columns entity_type, entity_id, date, score
