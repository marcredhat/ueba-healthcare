// 04_features_cloud.pq
// Hourly feature extractor — inlined-union form (file 01 pattern).
// Every union branch repeats the full base pipeline because SDL PowerQuery
// does NOT support `let X = (subquery)` for query aliasing. `union` is also
// capped at 10 subqueries; >10 features use a nested union.
//
// 04_features_cloud.pq
// Hourly USER data-transfer features.
// class_uid=4001 + event_category=data_transfer.
// HL7, FHIR, exports, imports, email, print. Entity = actor.username.
// Note: sum(record_count) totals exported records (only export events carry it).

| union
(
  | union
      (
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
        | columns entity_id, hour_ts, feature_name = "dt_events", value = dt_events
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "dt_failures", value = dt_failures
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "export_initiated", value = export_initiated
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "export_completed", value = export_completed
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "import_initiated", value = import_initiated
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "import_completed", value = import_completed
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "email_notifications", value = email_notifications
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "report_generated", value = report_generated
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "fhir_requests", value = fhir_requests
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "hl7_received", value = hl7_received
      )
),
(
  | union
      (
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
        | columns entity_id, hour_ts, feature_name = "hl7_sent", value = hl7_sent
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "print_jobs", value = print_jobs
      ),
      (
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
        | columns entity_id, hour_ts, feature_name = "total_records_exported", value = total_records_exported
      ),
      (
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
      )
)
| let entity_type = "user", family = "cloud"
| columns entity_type, entity_id, hour_ts, family, feature_name, value
| savelookup 'ueba_features_hourly', 'merge'
