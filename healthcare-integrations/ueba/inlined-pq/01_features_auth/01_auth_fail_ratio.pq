// Auto-generated from 01_features_auth.pq
// Feature: auth_fail_ratio
// Writes to: ueba_features_hourly

class_uid = 3002
    | parse '"username": "$entity_id{regex=[^"]+}$"'    from message
    | parse '"outcome": "$outcome{regex=[^"]+}$"'       from message
    | parse '"event_type": "$event_type{regex=[^"]+}$"' from message
    | group
        auth_total            = count(),
        auth_fail             = count(outcome = "failure"),
        auth_succ             = count(outcome = "success"),
        login_success         = count(event_type = "USER_LOGIN_SUCCESS"),
        login_failure         = count(event_type = "USER_LOGIN_FAILURE"),
        logout                = count(event_type = "USER_LOGOUT"),
        session_timeout       = count(event_type = "SESSION_TIMEOUT"),
        mfa_success           = count(event_type = "MFA_CHALLENGE_SUCCESS"),
        mfa_failure           = count(event_type = "MFA_CHALLENGE_FAILURE"),
        password_change       = count(event_type = "PASSWORD_CHANGE"),
        password_reset_req    = count(event_type = "PASSWORD_RESET_REQUEST"),
        account_locked        = count(event_type = "ACCOUNT_LOCKED"),
        account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" AND outcome = "failure")
      by hour_ts = timebucket('1 hour'), entity_id
    | filter entity_id = *
    | let
        auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
        mfa_fail_ratio  = (mfa_success + mfa_failure) > 0
                            ? (1.0 * mfa_failure / (mfa_success + mfa_failure))
                            : 0.0
| columns entity_id, hour_ts, feature_name = "auth_fail_ratio",       value = auth_fail_ratio
| let entity_type = "user", family = "auth"
| columns entity_type, entity_id, hour_ts, family, feature_name, value
| savelookup 'ueba_features_hourly', 'merge'
