// 01_features_auth.pq
// Hourly USER authentication features (class_uid=3002) -> ueba_features_hourly
//
// SDL PowerQuery rules applied:
//   - `let X = ( ... )` for a subquery alias is NOT supported. Every union branch
//     must be a self-contained pipeline; the base query is repeated in each.
//   - `union` supports at most 10 subqueries; 15 features are split into a 2-level
//     nested union (10 + 5) to stay within the limit.
//   - Equality in filters uses `=`, not `==`. `==` is documented as a synonym but
//     `=` is the canonical form in user-tested queries on this tenant.
//   - `extend` -> `| let col = expr` for derived columns.
//   - `if(cond,a,b)` -> ternary `cond ? a : b`.
//   - `and/or` -> `&&/||`.
//   - Persistence: `| savelookup '<name>'[, 'merge']`.

| union
(
  | union
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "auth_total", value = auth_total
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "auth_fail", value = auth_fail
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "auth_succ", value = auth_succ
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "auth_fail_ratio", value = auth_fail_ratio
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "login_success", value = login_success
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "login_failure", value = login_failure
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "logout", value = logout
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "session_timeout", value = session_timeout
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "mfa_success", value = mfa_success
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "mfa_failure", value = mfa_failure
    )
),
(
  | union
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "mfa_fail_ratio", value = mfa_fail_ratio
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "password_change", value = password_change
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "password_reset_req", value = password_reset_req
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "account_locked", value = account_locked
    ),
    (
      class_uid = 3002
      | parse '"username": "$entity_id{regex=[^"]+}$"' from message
      | parse '"outcome": "$outcome{regex=[^"]+}$"' from message
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
          account_unlocked_fail = count(event_type = "ACCOUNT_UNLOCKED" && outcome = "failure")
        by hour_ts = timebucket('1 hour'), entity_id
      | filter entity_id = *
      | let
          auth_fail_ratio = auth_total > 0 ? (1.0 * auth_fail / auth_total) : 0.0,
          mfa_fail_ratio  = (mfa_success + mfa_failure) > 0 ? (1.0 * mfa_failure / (mfa_success + mfa_failure)) : 0.0
      | columns entity_id, hour_ts, feature_name = "account_unlocked_fail", value = account_unlocked_fail
    )
)
| let entity_type = "user", family = "auth"
| columns entity_type, entity_id, hour_ts, family, feature_name, value
| savelookup 'ueba_features_hourly', 'merge'
