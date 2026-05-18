// Auto-generated from 05_features_healthcare.pq
// Feature: hba_events
// Writes to: ueba_features_hourly

| filter( class_uid = 3002 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"type": "$card_type{regex=[^"]+}$"'           from message
            | parse '"pin_type": "$pin_type{regex=[^"]+}$"'        from message
            | parse '"attempts_remaining": $attempts_remaining{regex=[0-9]+}$' from message
            | group
                card_events            = count( event_cat = "card_operations" ),
                card_failures          = count( event_cat = "card_operations" AND outcome = "failure" ),
                card_read_success      = count( event_type = "CARD_READ_SUCCESS" ),
                card_read_failure      = count( event_type = "CARD_READ_FAILURE" ),
                card_pin_verified      = count( event_type = "CARD_PIN_VERIFIED" ),
                card_pin_failed        = count( event_type = "CARD_PIN_FAILED" ),
                card_pin_blocked       = count( event_type = "CARD_PIN_BLOCKED" ),
                card_removed           = count( event_type = "CARD_REMOVED" ),
                card_decryption        = count( event_type = "CARD_DECRYPTION_SUCCESS" ),
                card_signature_created = count( event_type = "CARD_SIGNATURE_CREATED" ),
                card_auth_success      = count( event_type = "CARD_AUTHENTICATION_SUCCESS" ),
                card_auth_failed       = count( event_type = "CARD_AUTHENTICATION_FAILED" ),
                smcb_events            = count( card_type = "SMC-B" ),
                hba_events             = count( card_type = "HBA" ),
                qes_pin_attempts       = count( pin_type = "PIN.QES" ),
                low_attempts_remaining = count( attempts_remaining = 1 OR attempts_remaining = 0 )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
            | filter card_events > 0
            | let
                card_failure_ratio = card_events > 0 ? (1.0 * card_failures / card_events) : 0.0
        | columns entity_id, hour_ts, feature_name = "hba_events", value = hba_events
| let entity_type = "host", family = "healthcare"
| columns entity_type, entity_id, hour_ts, family, feature_name, value
| savelookup 'ueba_features_hourly', 'merge'
