// 06_peers_dynamic.pq
// Weekly DYNAMIC peer assignment for USER and HOST entities.
//
// USER peers : derived from (role, hospital_id) in auth/endpoint events.
// HOST peers : derived from (hostname stem, location).
//
// Output schema (matches /datatables/ueba_peer_membership):
//   entity_type, entity_id, peer_id, valid_from, valid_to
//
| union
    (
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
    ),
    (
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
    )
| columns entity_type, entity_id, peer_id, valid_from, valid_to
