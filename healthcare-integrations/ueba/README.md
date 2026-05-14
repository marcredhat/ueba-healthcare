# SDL UEBA Query Pack (tenant-adapted)

Statistical UEBA on SentinelOne Singularity Data Lake (SDL), adapted to this
tenant's healthcare/TI schema (JSON payload in `message`, German hospitals,
gematik Telematik Infrastruktur, SMC-B/HBA cards, Konnektor, HL7/FHIR).

## File order (run in this order)

1. `00_datatables_schema.md` — datatables you must create (one-time).
2. `01_features_auth.pq` — hourly USER auth (class_uid=3002).
3. `02_features_endpoint.pq` — hourly HOST endpoint (3002+4001).
4. `03_features_network.pq` — hourly HOST TI/network (4001 ti_connection: Konnektor, VPN, certs).
5. `04_features_cloud.pq` — hourly USER data-transfer (4001 data_transfer: HL7/FHIR/exports/prints).
6. `05_features_healthcare.pq` — hourly HOST card ops (3002 card_operations: SMC-B/HBA/PIN/signature).
7. `06_peers_dynamic.pq` — weekly dynamic peers; USER peers by (role, hospital_id); HOST peers by hostname+location.
8. `07_baselines_entity.pq` — nightly per-entity baselines (28d).
9. `08_baselines_peer.pq` — nightly per-peer baselines (28d).
10. `09_scoring.pq` — hourly anomaly scoring + family scores.
11. `10_risk_daily.pq` — daily entity risk with 48h half-life decay.
12. `11_alerts.pq` — UEBA alerts with explanations.

> Files 07–11 use only standard SDL primitives and the verified patterns from
> `SDL_POWERQUERY_QUIRKS.md`; rename fields if your tenant differs.

## Tenant schema notes

This tenant emits OCSF `class_uid` but the OCSF nested paths (`actor.user.name`,
`src_endpoint.ip`, etc.) are **null**. All useful fields live inside a JSON
string in `message`. The pack extracts them with `parse ... regex=[^"]+` and
`parse ... regex=[0-9]+`.

### Populated class_uids (last 24h sample)
- `3002` (Authentication) — login, logout, MFA, password ops, account lockouts, card ops
- `4001` (Network) — data_transfer (HL7/FHIR/exports/prints) + ti_connection (Konnektor/VPN/certs)
- `1001` (File) — sparse (1 event in sample)
- Others (`1007`, `4002`, `4003`, `6003`) — absent in this tenant

### Key JSON keys in `message`
- `event_type`, `event_category`, `outcome`, `severity`, `timestamp`
- `actor.username`, `actor.role`, `actor.department`, `actor.user_id`
- `client.ip`, `client.user_agent`, `client.device_type`
- `source.hostname`, `source.application`, `source.ip`
- `organization.hospital_id`, `organization.hospital_name`, `organization.location`
- `facility.bsnr`, `facility.name`, `facility.location`
- `konnektor.vendor`, `konnektor.serial_number`, `konnektor.telematik_id`
- `card.type` (SMC-B / HBA), `card.iccsn`, `card.terminal_id`
- `details.record_count` (numeric, on DATA_EXPORT_COMPLETED)

### Entity decisions
- **USER entity** = `lower(actor.username)` for auth/data-transfer.
- **HOST entity** = `source.hostname` for endpoint/TI/card families.
- **Card events have NO actor.username** in this tenant — they are bound to
  the card/terminal, so card features (file 05) are HOST-level, not user-level.

## Conventions

- All feature rows are unpivoted to `(entity_type, entity_id, hour_ts, family, feature_name, value)` via `union` of per-feature SELECTs.
- Datatables (see `00_datatables_schema.md`):
  - `ueba_features_hourly`, `ueba_baselines_entity`, `ueba_baselines_peer`,
    `ueba_peer_membership`, `ueba_entity_risk`, `ueba_alerts`, `ueba_watchlist`,
    `ueba_service_accounts`.

## SDL PowerQuery rules (verified on this tenant)
See `SDL_POWERQUERY_QUIRKS.md`. Top hits:
- Use `timebucket('1 hour')` (no `bin`).
- Use `count(condition)` (no `countif`).
- Put **all** `parse` first, then `group`; never `filter`/`extend` between them.
- Drop nulls post-group with `filter <col> = *`.
- `dcount(parsed_field)` 500s — use 2-stage subqueries (planned `12_distinct_count_features.pq`).
- `sum(if(...))` 500s — use plain `sum(field)`.

## Schedules
- Hourly: `01..05` feature extractors, `09` scoring.
- Daily (02:00 local): `07`, `08`, `10`, `11`.
- Weekly (Mon 03:00): `06` dynamic peers.

## Smoke status (last verified)
- 01 (user auth): PASS — produces ~15 rows/hour for active users.
- 02 (host endpoint): PASS — covers avelios-app/avelios-int and omniconnect hosts.
- 03 (host TI/network): PASS — Konnektor/VPN/cert events per omniconnect host.
- 04 (user data transfer): PASS — HL7/FHIR/exports/prints with record_count sums.
- 05 (host healthcare/card): PASS — card ops per omniconnect host (no users tied to cards).
- 06 (peers): PASS — USER peers (role+hospital) and HOST peers (hostname+location).
