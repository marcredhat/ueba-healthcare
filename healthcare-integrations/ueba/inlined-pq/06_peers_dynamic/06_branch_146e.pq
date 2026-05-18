// Auto-generated from 06_peers_dynamic.pq
// Feature: branch_146e
// Writes to: ueba_features_hourly

class_uid = 3002 OR class_uid = 4001
      | parse '"username": "$entity_id{regex=[^"]+}$"'    from message
      | parse '"role": "$role{regex=[^"]+}$"'             from message
      | parse '"hospital_id": "$hospital{regex=[^"]+}$"'  from message
      | group n = count() by entity_id, role, hospital, bucket = timebucket('1 day')
      | filter entity_id = *
      | filter role = *
      | filter hospital = *
      | columns
          entity_type = "user",
          entity_id,
          peer_id    = format("role=%s|hosp=%s", role, hospital),
          valid_from = bucket,
          valid_to   = bucket
| columns entity_type, entity_id, peer_id, valid_from, valid_to
