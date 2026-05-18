// Auto-generated from 12_distinct_count_features.pq
// Feature: distinct_destinations
// Writes to: ueba_features_hourly

| filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"username": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"destination": "$v{regex=[^"]+}$"'            from message
            | group inner_n = count( event_cat = "data_transfer" )
                    by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "user", entity_id, hour_ts,
                      family = "cloud", feature_name = "distinct_destinations", value
| savelookup 'ueba_features_hourly', 'merge'
