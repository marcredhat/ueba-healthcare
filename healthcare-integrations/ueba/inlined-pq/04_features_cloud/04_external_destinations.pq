// Auto-generated from 04_features_cloud.pq
// Feature: external_destinations
// Writes to: ueba_features_hourly

| filter( class_uid = 4001 )
            | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
            | parse '"username": "$entity_id{regex=[^"]+}$"'       from message
            | parse '"event_type": "$event_type{regex=[^"]+}$"'    from message
            | parse '"outcome": "$outcome{regex=[^"]+}$"'          from message
            | parse '"destination": "$destination{regex=[^"]+}$"'  from message
            | parse '"record_count": $record_count{regex=[0-9]+}$' from message
            | group
                dt_events              = count( event_cat = "data_transfer" ),
                dt_failures            = count( event_cat = "data_transfer" AND outcome = "failure" ),
                export_initiated       = count( event_type = "DATA_EXPORT_INITIATED" ),
                export_completed       = count( event_type = "DATA_EXPORT_COMPLETED" ),
                import_initiated       = count( event_type = "DATA_IMPORT_INITIATED" ),
                import_completed       = count( event_type = "DATA_IMPORT_COMPLETED" ),
                email_notifications    = count( event_type = "EMAIL_NOTIFICATION_SENT" ),
                report_generated       = count( event_type = "REPORT_GENERATED" ),
                fhir_requests          = count( event_type = "FHIR_API_REQUEST" ),
                hl7_received           = count( event_type = "HL7_MESSAGE_RECEIVED" ),
                hl7_sent               = count( event_type = "HL7_MESSAGE_SENT" ),
                print_jobs             = count( event_type = "PRINT_JOB_SUBMITTED" ),
                total_records_exported = sum( record_count ),
                external_destinations  = count( destination = "External Specialist" )
              by hour_ts = timebucket('1 hour'), entity_id
            | filter entity_id = *
        | columns entity_id, hour_ts, feature_name = "external_destinations", value = external_destinations
| let entity_type = "user", family = "cloud"
| columns entity_type, entity_id, hour_ts, family, feature_name, value
| savelookup 'ueba_features_hourly', 'merge'
