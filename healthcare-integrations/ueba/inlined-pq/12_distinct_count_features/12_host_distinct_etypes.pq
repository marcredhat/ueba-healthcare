// Auto-generated from 12_distinct_count_features.pq
// Feature: host_distinct_etypes
// Writes to: ueba_features_hourly

| filter( class_uid = 3002 OR class_uid = 4001 )
            | parse '"hostname": "$entity_id{regex=[^"]+}$"' from message
            | parse '"event_type": "$v{regex=[^"]+}$"'       from message
            | group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "host", entity_id, hour_ts,
                      family = "endpoint", feature_name = "host_distinct_etypes", value
| savelookup 'ueba_features_hourly', 'merge'
