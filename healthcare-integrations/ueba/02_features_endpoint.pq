// 02_features_endpoint.pq
// Hourly HOST endpoint features (source.hostname = application/TI server).
// Combines class_uid 3002 (auth) + 4001 (data/TI).
// Tracks activity intensity, severity, failure ratio per host.

let base =
  (
    | filter( class_uid == 3002 || class_uid == 4001 )
    | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
    | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
    | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
    | parse '"severity": "$severity{regex=[^"]+}$"'        from message
    | group
        host_events        = count(),
        host_failures      = count( outcome == "failure" ),
        host_infos         = count( outcome == "info" ),
        host_high_severity = count( severity == "HIGH" || severity == "CRITICAL" ),
        host_auth_events   = count( class_uid == 3002 ),
        host_data_events   = count( event_cat == "data_transfer" ),
        host_ti_events     = count( event_cat == "ti_connection" ),
        host_card_events   = count( event_cat == "card_operations" )
      by hour_ts = timebucket('1 hour'), entity_id
    | filter entity_id = *
    | let
        host_failure_ratio = host_events > 0 ? (1.0 * host_failures / host_events) : 0.0
  );

| union
  ( base | columns entity_id, hour_ts, feature_name = "host_events",          value = host_events ),
  ( base | columns entity_id, hour_ts, feature_name = "host_failures",        value = host_failures ),
  ( base | columns entity_id, hour_ts, feature_name = "host_infos",           value = host_infos ),
  ( base | columns entity_id, hour_ts, feature_name = "host_failure_ratio",   value = host_failure_ratio ),
  ( base | columns entity_id, hour_ts, feature_name = "host_high_severity",   value = host_high_severity ),
  ( base | columns entity_id, hour_ts, feature_name = "host_auth_events",     value = host_auth_events ),
  ( base | columns entity_id, hour_ts, feature_name = "host_data_events",     value = host_data_events ),
  ( base | columns entity_id, hour_ts, feature_name = "host_ti_events",       value = host_ti_events ),
  ( base | columns entity_id, hour_ts, feature_name = "host_card_events",     value = host_card_events )
| let entity_type = "host", family = "endpoint"
| columns entity_type, entity_id, hour_ts, family, feature_name, value
| savelookup 'ueba_features_hourly', 'merge'
