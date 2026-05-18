// 03_features_network.pq
// Hourly feature extractor — inlined-union form (file 01 pattern).
// Every union branch repeats the full base pipeline because SDL PowerQuery
// does NOT support `let X = (subquery)` for query aliasing. `union` is also
// capped at 10 subqueries; >10 features use a nested union.
//
// 03_features_network.pq
// Hourly HOST TI/network features.
// class_uid=4001 + event_category=ti_connection.
// Konnektor lifecycle, VPN tunnels, TI availability, certificates.

| union
(
  | union
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "ti_events", value = ti_events
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "ti_failures", value = ti_failures
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "ti_failure_ratio", value = ti_failure_ratio
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "konnektor_connected", value = konnektor_connected
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "konnektor_disconnected", value = konnektor_disconnected
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "konnektor_health_check", value = konnektor_health_check
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "konnektor_flap_score", value = konnektor_flap_score
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "vpn_tunnel_failed", value = vpn_tunnel_failed
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "vpn_tunnel_reconnect", value = vpn_tunnel_reconnect
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "cert_expired", value = cert_expired
      )
),
(
  | union
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "cert_expiring", value = cert_expiring
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "cert_valid", value = cert_valid
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "ti_service_unavailable", value = ti_service_unavailable
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "ti_service_available", value = ti_service_available
      ),
      (
        | filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"severity": "$severity{regex=[^"]+}$"'        from message
            | group
                ti_events              = count( event_cat = "ti_connection" ),
                ti_failures            = count( event_cat = "ti_connection" AND outcome = "failure" ),
                konnektor_connected    = count( event_type = "KONNEKTOR_CONNECTED" ),
                konnektor_disconnected = count( event_type = "KONNEKTOR_DISCONNECTED" ),
                konnektor_health_check = count( event_type = "KONNEKTOR_HEALTH_CHECK" ),
                vpn_tunnel_failed      = count( event_type = "VPN_TUNNEL_FAILED" ),
                vpn_tunnel_reconnect   = count( event_type = "VPN_TUNNEL_RECONNECT" ),
                cert_expired           = count( event_type = "CERTIFICATE_EXPIRED" ),
                cert_expiring          = count( event_type = "CERTIFICATE_EXPIRING" ),
                cert_valid             = count( event_type = "CERTIFICATE_VALID" ),
                ti_service_unavailable = count( event_type = "TI_SERVICE_UNAVAILABLE" ),
                ti_service_available   = count( event_type = "TI_SERVICE_AVAILABLE" ),
                high_sev_events        = count( event_cat = "ti_connection" AND (severity = "HIGH" OR severity = "CRITICAL") )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | let
                konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed,
                ti_failure_ratio     = ti_events > 0 ? (1.0 * ti_failures / ti_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "high_sev_events", value = high_sev_events
      )
)
| let entity_type = "host", family = "network"
| columns entity_type, entity_id, hour_ts, family, feature_name, value
| savelookup 'ueba_features_hourly', 'merge'
