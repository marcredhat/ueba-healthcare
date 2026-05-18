// Auto-generated from 12_distinct_count_features.pq
// Feature: distinct_telematik_ids
// Writes to: ueba_features_hourly

| filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"telematik_id": "$v{regex=[^"]+}$"'           from message
            | group inner_n = count( event_cat = "ti_connection" )
                    by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "host", entity_id, hour_ts,
                      family = "network", feature_name = "distinct_telematik_ids", value
| savelookup 'ueba_features_hourly', 'merge'
