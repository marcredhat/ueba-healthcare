// PENDING REFACTOR: uses `let X = (multi-step subquery)` extensively.
//   SDL does NOT support let-as-subquery-alias. Split into multiple sequential
//   queries that materialise intermediates via | savelookup and read back via
//   dataset 'config://datatables/...'.
//
// 10_risk_daily.pq
// Daily entity risk with exponential decay.
//   R_today = sum_family( w_family * family_daily )
//   R_t     = max(R_today, R_{t-1} * exp(-lambda * dt_hours))
// half-life = 48h  =>  lambda = ln(2)/48 ~= 0.01444

let weights = pack_dict(
  "auth",     1.0,
  "endpoint", 1.3,
  "network",  0.8,
  "cloud",    1.4,
  "web",      0.6,
  "dns",      0.7,
  "file",     0.9
);

let today_d = bin(now(), 1d);

let today_family_daily =
  dataset 'config://datatables/ueba_family_scores_hourly'
  | filter hour_ts >= today_d - 1d && hour_ts < today_d
  | group entity_type, entity_id, family by
      family_daily = percentile(family_score, 95);

let today_risk =
  today_family_daily
  | let w = weights[family]
  | group entity_type, entity_id by today_risk = sum(family_daily * todouble(w));

let yday_risk =
  dataset 'config://datatables/ueba_entity_risk'
  | filter date = (today_d - 1d)
  | project entity_type, entity_id, yday_score = score;

today_risk
| join kind=leftouter yday_risk on entity_type, entity_id
| let decayed = coalesce(yday_score, 0.0) * exp(-0.01444 * 24.0)
| let score   = max_of(today_risk, decayed)
| let date    = today_d
| project entity_type, entity_id, date, score
| savelookup 'ueba_entity_risk', 'merge'
