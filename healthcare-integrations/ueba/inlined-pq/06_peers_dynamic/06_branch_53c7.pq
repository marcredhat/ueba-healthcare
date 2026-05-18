// Auto-generated from 06_peers_dynamic.pq
// Feature: branch_53c7
// Writes to: ueba_features_hourly

class_uid = 3002 OR class_uid = 4001
      | parse '"hostname": "$entity_id{regex=[^"]+}$"' from message
      | parse '"location": "$loc{regex=[^"]+}$"'       from message
      | group n = count() by entity_id, loc, bucket = timebucket('1 day')
      | filter entity_id = *
      | columns
          entity_type = "host",
          entity_id,
          peer_id    = format("host=%s|loc=%s", entity_id, loc),
          valid_from = bucket,
          valid_to   = bucket
| columns entity_type, entity_id, peer_id, valid_from, valid_to
