// 06_peers_dynamic.pq
// Weekly DYNAMIC peer assignment for USER and HOST entities.
//
// USER peers : (role, hospital_id)
// HOST peers : (hostname stem, location)
//
// Runs via run_pq_combined.py (per-branch READ -> putFile to /datatables/ueba_peer_membership)
// or as a single Event-Search compatible | union (works in UI for visual sanity).
//
| union
    (
      class_uid = 3002 || class_uid = 4001
      | parse '"username": "$entity_id{regex=[^"]+}$"'    from message
      | parse '"role": "$role{regex=[^"]+}$"'             from message
      | parse '"hospital_id": "$hospital{regex=[^"]+}$"'  from message
      | group n = count() by entity_id, role, hospital
      | filter entity_id = *
      | filter role = *
      | filter hospital = *
      | columns
          entity_id,
          peer_id    = strcat("role=", role, "|hosp=", hospital),
          valid_from = timebucket('1 day'),
          valid_to   = timebucket('1 day'),
          entity_type = "user"
    ),
    (
      class_uid = 3002 || class_uid = 4001
      | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
      | parse '"location": "$loc{regex=[^"]+}$"'             from message
      | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
      | group n = count() by entity_id, loc, event_cat
      | filter entity_id = *
      | columns
          entity_id,
          peer_id    = strcat("host_fam=", entity_id, "|loc=", coalesce(loc, "unknown")),
          valid_from = timebucket('1 day'),
          valid_to   = timebucket('1 day'),
          entity_type = "host"
    )
| columns entity_type, entity_id, peer_id, valid_from, valid_to
| savelookup 'ueba_peer_membership', 'merge'
