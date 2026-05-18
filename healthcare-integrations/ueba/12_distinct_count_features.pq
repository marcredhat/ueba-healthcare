// 12_distinct_count_features.pq
// Hourly distinct-count features. Each branch is a full self-contained
// pipeline using the verified 2-stage `group(inner) | group(outer)` pattern
// (dcount on parsed fields 500s when combined with timebucket). Branches
// are unioned (max 10 per union, nested for >10). Each branch already
// emits the final schema (entity_type, entity_id, hour_ts, family,
// feature_name, value), so the merged stream is written directly.
//
| union
(
  | union
      (
            | filter( class_uid = 3002 )
            | parse '"username": "$entity_id{regex=[^"]+}$"' from message
            | parse '"ip": "$v{regex=[^"]+}$"'               from message
            | group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "user", entity_id, hour_ts,
                      family = "auth", feature_name = "distinct_src_ip", value
      ),
      (
            | filter( class_uid = 3002 )
            | parse '"username": "$entity_id{regex=[^"]+}$"' from message
            | parse '"hostname": "$v{regex=[^"]+}$"'         from message
            | group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "user", entity_id, hour_ts,
                      family = "auth", feature_name = "distinct_src_host", value
      ),
      (
            | filter( class_uid = 3002 OR class_uid = 4001 )
            | parse '"hostname": "$entity_id{regex=[^"]+}$"' from message
            | parse '"username": "$v{regex=[^"]+}$"'         from message
            | group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "host", entity_id, hour_ts,
                      family = "endpoint", feature_name = "host_distinct_users", value
      ),
      (
            | filter( class_uid = 3002 OR class_uid = 4001 )
            | parse '"hostname": "$entity_id{regex=[^"]+}$"' from message
            | parse '"event_type": "$v{regex=[^"]+}$"'       from message
            | group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "host", entity_id, hour_ts,
                      family = "endpoint", feature_name = "host_distinct_etypes", value
      ),
      (
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
      ),
      (
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
      ),
      (
            | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"username": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"export_type": "$v{regex=[^"]+}$"'            from message
            | group inner_n = count( event_cat = "data_transfer" )
                    by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "user", entity_id, hour_ts,
                      family = "cloud", feature_name = "distinct_export_types", value
      ),
      (
            | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"username": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"message_type": "$v{regex=[^"]+}$"'           from message
            | group inner_n = count( event_cat = "data_transfer" )
                    by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "user", entity_id, hour_ts,
                      family = "cloud", feature_name = "distinct_msg_types", value
      ),
      (
            | filter( class_uid = 3002 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"iccsn": "$v{regex=[^"]+}$"'                  from message
            | group inner_n = count( event_cat = "card_operations" )
                    by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "host", entity_id, hour_ts,
                      family = "healthcare", feature_name = "distinct_cards", value
      ),
      (
            | filter( class_uid = 3002 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"terminal_id": "$v{regex=[^"]+}$"'            from message
            | group inner_n = count( event_cat = "card_operations" )
                    by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "host", entity_id, hour_ts,
                      family = "healthcare", feature_name = "distinct_terminals", value
      )
),
(
  | union
      (
            | filter( class_uid = 3002 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"type": "$v{regex=[^"]+}$"'                   from message
            | group inner_n = count( event_cat = "card_operations" )
                    by hour_ts = timebucket('1 hour'), entity_id, v
            | filter entity_id = *
            | filter v = *
            | group value = count() by hour_ts, entity_id
            | columns entity_type = "host", entity_id, hour_ts,
                      family = "healthcare", feature_name = "distinct_card_types", value
      )
)
| savelookup 'ueba_features_hourly', 'merge'
