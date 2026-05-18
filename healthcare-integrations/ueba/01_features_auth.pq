// 01_features_auth.pq
// Hourly USER authentication features (healthcare tenant).
// class_uid=3002 -> ueba_features_hourly.
//
// CONCISE FORM. The Python orchestrator (`run_pq.py::_expand_let_base`)
// inlines `base` into each union branch at submission time because
// this tenant's PowerQuery parser rejects `let X = ( subquery )`. The
// resulting wire query is the long inlined-union form documented in
// `SDL_POWERQUERY_QUIRKS.md`.
//
// SDL PowerQuery rules verified on this tenant:
//   - timebucket('1 hour') (NOT bin())
//   - count(condition) (NOT countif)
//   - All parse commands first, THEN group; do not insert filter between
//   - Post-group null filter: `filter <col> = *` (NOT isnotnull)
//   - dcount on parse-extracted fields 500s (see 12_*)
//   - sum(if(...)) inside group 500s
//   - Boolean ops are `AND` / `OR` (NOT `&&` / `||`)
//   - Equality is `=` (NOT `==`)

let base =
  (
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
  );

| union
    ( base | columns entity_id, hour_ts, feature_name = "auth_total",            value = auth_total            ),
    ( base | columns entity_id, hour_ts, feature_name = "auth_fail",             value = auth_fail             ),
    ( base | columns entity_id, hour_ts, feature_name = "auth_succ",             value = auth_succ             ),
    ( base | columns entity_id, hour_ts, feature_name = "auth_fail_ratio",       value = auth_fail_ratio       ),
    ( base | columns entity_id, hour_ts, feature_name = "login_success",         value = login_success         ),
    ( base | columns entity_id, hour_ts, feature_name = "login_failure",         value = login_failure         ),
    ( base | columns entity_id, hour_ts, feature_name = "logout",                value = logout                ),
    ( base | columns entity_id, hour_ts, feature_name = "session_timeout",       value = session_timeout       ),
    ( base | columns entity_id, hour_ts, feature_name = "mfa_success",           value = mfa_success           ),
    ( base | columns entity_id, hour_ts, feature_name = "mfa_failure",           value = mfa_failure           ),
    ( base | columns entity_id, hour_ts, feature_name = "mfa_fail_ratio",        value = mfa_fail_ratio        ),
    ( base | columns entity_id, hour_ts, feature_name = "password_change",       value = password_change       ),
    ( base | columns entity_id, hour_ts, feature_name = "password_reset_req",    value = password_reset_req    ),
    ( base | columns entity_id, hour_ts, feature_name = "account_locked",        value = account_locked        ),
    ( base | columns entity_id, hour_ts, feature_name = "account_unlocked_fail", value = account_unlocked_fail )
| let entity_type = "user", family = "auth"
| columns entity_type, entity_id, hour_ts, family, feature_name, value
| savelookup 'ueba_features_hourly', 'merge'
