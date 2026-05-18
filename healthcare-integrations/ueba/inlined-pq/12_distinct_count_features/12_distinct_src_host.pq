// Auto-generated from 12_distinct_count_features.pq
// Feature: distinct_src_host
// Writes to: ueba_features_hourly

| filter( class_uid = 3002 )
            | parse '"username": "$entity_id{regex=[^"]+}$"' from message
            | parse '"hostname": "$v{regex=[^"]+}$"'         from message
            | group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "user", entity_id, hour_ts,
                      family = "auth", feature_name = "distinct_src_host", value
| savelookup 'ueba_features_hourly', 'merge'
