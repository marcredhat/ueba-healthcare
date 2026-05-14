// 12_distinct_count_features.pq
// Hourly distinct-count features via verified 2-stage pattern:
//   1) parse + group(entity, hour, field) -> inner row per distinct (field, entity, hour)
//   2) filter nulls    -> drop null entity / null field
//   3) group(entity, hour) -> count() -> distinct count
//
// SDL constraint: dcount(parsed_field) 500s when combined with timebucket + group.
// This file emits one distinct-count feature per subquery, then unions them.
// Run hourly. Writes to ueba_features_hourly.

// =========================================================================
// AUTH: distinct_src_ip and distinct_src_host per USER (class_uid=3002)
// =========================================================================
let auth_distinct_src_ip =
  (
    | filter( class_uid == 3002 )
    | parse '"username": "$entity_id{regex=[^"]+}$"' from message
    | parse '"ip": "$v{regex=[^"]+}$"'               from message
    | group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "user", entity_id, hour_ts,
              family = "auth", feature_name = "distinct_src_ip", value
  );

let auth_distinct_src_host =
  (
    | filter( class_uid == 3002 )
    | parse '"username": "$entity_id{regex=[^"]+}$"' from message
    | parse '"hostname": "$v{regex=[^"]+}$"'         from message
    | group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "user", entity_id, hour_ts,
              family = "auth", feature_name = "distinct_src_host", value
  );

// =========================================================================
// ENDPOINT (HOST): distinct_users and distinct_etypes per HOST
// =========================================================================
let host_distinct_users =
  (
    | filter( class_uid == 3002 or class_uid == 4001 )
    | parse '"hostname": "$entity_id{regex=[^"]+}$"' from message
    | parse '"username": "$v{regex=[^"]+}$"'         from message
    | group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "host", entity_id, hour_ts,
              family = "endpoint", feature_name = "host_distinct_users", value
  );

let host_distinct_etypes =
  (
    | filter( class_uid == 3002 or class_uid == 4001 )
    | parse '"hostname": "$entity_id{regex=[^"]+}$"' from message
    | parse '"event_type": "$v{regex=[^"]+}$"'       from message
    | group inner_n = count() by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "host", entity_id, hour_ts,
              family = "endpoint", feature_name = "host_distinct_etypes", value
  );

// =========================================================================
// NETWORK/TI (HOST): distinct_telematik_ids per Konnektor host
// =========================================================================
let host_distinct_telematik_ids =
  (
    | filter( class_uid == 4001 )
    | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
    | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
    | parse '"telematik_id": "$v{regex=[^"]+}$"'           from message
    | group inner_n = count( event_cat == "ti_connection" )
            by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "host", entity_id, hour_ts,
              family = "network", feature_name = "distinct_telematik_ids", value
  );

// =========================================================================
// DATA TRANSFER (USER): distinct destinations, export_types, msg_types
// =========================================================================
let user_distinct_destinations =
  (
    | filter( class_uid == 4001 )
    | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
    | parse '"username": "$entity_id{regex=[^"]+}$"'       from message
    | parse '"destination": "$v{regex=[^"]+}$"'            from message
    | group inner_n = count( event_cat == "data_transfer" )
            by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "user", entity_id, hour_ts,
              family = "cloud", feature_name = "distinct_destinations", value
  );

let user_distinct_export_types =
  (
    | filter( class_uid == 4001 )
    | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
    | parse '"username": "$entity_id{regex=[^"]+}$"'       from message
    | parse '"export_type": "$v{regex=[^"]+}$"'            from message
    | group inner_n = count( event_cat == "data_transfer" )
            by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "user", entity_id, hour_ts,
              family = "cloud", feature_name = "distinct_export_types", value
  );

let user_distinct_msg_types =
  (
    | filter( class_uid == 4001 )
    | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
    | parse '"username": "$entity_id{regex=[^"]+}$"'       from message
    | parse '"message_type": "$v{regex=[^"]+}$"'           from message
    | group inner_n = count( event_cat == "data_transfer" )
            by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "user", entity_id, hour_ts,
              family = "cloud", feature_name = "distinct_msg_types", value
  );

// =========================================================================
// HEALTHCARE / CARD (HOST): distinct cards, terminals, card types
// =========================================================================
let host_distinct_cards =
  (
    | filter( class_uid == 3002 )
    | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
    | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
    | parse '"iccsn": "$v{regex=[^"]+}$"'                  from message
    | group inner_n = count( event_cat == "card_operations" )
            by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "host", entity_id, hour_ts,
              family = "healthcare", feature_name = "distinct_cards", value
  );

let host_distinct_terminals =
  (
    | filter( class_uid == 3002 )
    | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
    | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
    | parse '"terminal_id": "$v{regex=[^"]+}$"'            from message
    | group inner_n = count( event_cat == "card_operations" )
            by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "host", entity_id, hour_ts,
              family = "healthcare", feature_name = "distinct_terminals", value
  );

let host_distinct_card_types =
  (
    | filter( class_uid == 3002 )
    | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
    | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
    | parse '"type": "$v{regex=[^"]+}$"'                   from message
    | group inner_n = count( event_cat == "card_operations" )
            by hour_ts = timebucket('1 hour'), entity_id, v
    | filter entity_id = *
    | filter v = *
    | group value = count() by hour_ts, entity_id
    | columns entity_type = "host", entity_id, hour_ts,
              family = "healthcare", feature_name = "distinct_card_types", value
  );

// =========================================================================
// UNION + WRITE
// =========================================================================
union
  auth_distinct_src_ip,
  auth_distinct_src_host,
  host_distinct_users,
  host_distinct_etypes,
  host_distinct_telematik_ids,
  user_distinct_destinations,
  user_distinct_export_types,
  user_distinct_msg_types,
  host_distinct_cards,
  host_distinct_terminals,
  host_distinct_card_types
| savelookup 'ueba_features_hourly', 'merge'
