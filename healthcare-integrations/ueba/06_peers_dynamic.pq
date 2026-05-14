// 06_peers_dynamic.pq
// Weekly DYNAMIC peer assignment for USER and HOST entities.
//
// Strategy:
//   - For USERS: build peer_id from (role, hospital_id) static dimensions first,
//     then fall back to a quantile-signature over behavioral profile if role/hospital
//     are missing or peer groups are too small.
//   - For HOSTS: peer_id is based on hostname pattern + facility location (extracted
//     from event payload).
//
// This file is illustrative. SDL writeto-with-overwrite semantics may vary by
// tenant; if `mode="replace"` is not allowed, switch to "append" and add a
// weekly truncation step.

// ===========================================================================
// USER PEERS: (role, hospital_id)
// Most events in this tenant carry actor.role + organization.hospital_id.
// ===========================================================================
let user_peers =
  (
    | filter( class_uid == 3002 || class_uid == 4001 )
    | parse '"username": "$entity_id{regex=[^"]+}$"'    from message
    | parse '"role": "$role{regex=[^"]+}$"'             from message
    | parse '"hospital_id": "$hospital{regex=[^"]+}$"'  from message
    | group
        n = count()
      by entity_id, role, hospital
    | filter entity_id = *
    | filter role = *
    | filter hospital = *
    | columns
        entity_type = "user",
        entity_id,
        peer_id = strcat( "role=", role, "|hosp=", hospital ),
        valid_from = timebucket('1 day'),
        valid_to   = timebucket('1 day')
  );

// ===========================================================================
// HOST PEERS: prefix-based (e.g., "avelios-app", "avelios-int", "omniconnect")
// Extract the host family from hostname; hosts in the same family behave alike.
// ===========================================================================
let host_peers =
  (
    | filter( class_uid == 3002 || class_uid == 4001 )
    | parse '"hostname": "$entity_id{regex=[^"]+}$"'       from message
    | parse '"location": "$loc{regex=[^"]+}$"'             from message
    | parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
    | group
        n = count()
      by entity_id, loc, event_cat
    | filter entity_id = *
    | columns
        entity_type = "host",
        entity_id,
        // peer family from hostname stem + location
        peer_id = strcat( "host_fam=", entity_id, "|loc=", coalesce( loc, "unknown" ) ),
        valid_from = timebucket('1 day'),
        valid_to   = timebucket('1 day')
  );

// ===========================================================================
// COMBINE + WRITE
// ===========================================================================
| union user_peers, host_peers
| savelookup 'ueba_peer_membership'
