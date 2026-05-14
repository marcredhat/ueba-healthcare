# UEBA Feature Extractors — Scientific Documentation (Files 01–12)

This document explains the **why and how** behind each UEBA file in this pack.
The pack implements **statistical (unsupervised) UEBA** — no labelled training set
is needed; instead, every entity is its own normal, with **peer baselines** as a
sanity check. The whole pipeline runs as native PowerQuery on SentinelOne
Singularity Data Lake (SDL).

Each section follows the same structure:

1. **What** the file does
2. **Why** it exists — the threat-detection or compliance rationale
3. **How** — statistical / mathematical basis
4. **Limitations** specific to this tenant

A separate section at the end discusses **improvements for healthcare UEBA**.

---

## Conceptual model

UEBA = **Entity** + **Feature** + **Baseline** + **Score** + **Risk**.

```
   raw events
       │
       ▼  parse JSON in `message` (01..05, 12)
   hourly features per entity
       │
       ▼  long history (07, 08)
   per-entity baseline μ,σ,q50,q90,q99
   per-peer baseline   μ,σ,q50,q90,q99
       │
       ▼  combine (09)
   hourly anomaly score per entity·family
       │
       ▼  aggregate + decay (10)
   daily risk per entity
       │
       ▼  threshold + explain (11)
   alerts
```

**Entity** is either a **user** (`actor.username`) or **host**
(`source.hostname`). Cards (SMC-B/HBA) are *not* entities — they have no user
binding in this tenant and are tracked as host-level features (file 05).

**Family** = `auth | endpoint | network | cloud | healthcare`. Families let us
write per-family thresholds and weights (file 10).

**Time grain** = hourly, because hospital workflows have strong intra-day shape
(rounds, shift changes, OR scheduling). A grain finer than an hour adds noise;
coarser than an hour hides shift-handover anomalies.

---

## File-by-file explanation

### `00_datatables_schema.md` — table contracts

Defines seven SDL datatables:

| Table | Role | Refresh |
|---|---|---|
| `ueba_features_hourly` | central wide-to-long feature store, one row per (entity, hour, feature) | append hourly, TTL 35 days |
| `ueba_baselines_entity` | μ, σ, q50, q90, q99 per (entity, feature) from last 28 days | replace nightly |
| `ueba_baselines_peer` | same, per (peer_id, feature) | replace nightly |
| `ueba_peer_membership` | mapping entity → peer_id with validity window | replace weekly |
| `ueba_entity_risk` | one row per (entity, day) — the decayed risk score | append daily |
| `ueba_alerts` | UEBA-fired alerts with explanation JSON | append on trigger |
| `ueba_watchlist`, `ueba_service_accounts` | side tables for risk multipliers and noise suppression | manual |

The long ("unpivoted") schema for features lets new features be added without DDL.

---

### `01_features_auth.pq` — User authentication, hourly

**What.** Per (user, hour), counts of authentication events filtered by
`class_uid=3002`. Computes 15 features: total events, success, failure,
success/failure ratio, login_success / login_failure / logout /
session_timeout, MFA success / failure / fail-ratio, password change / reset
request, account lockouts.

**Why.**

- **Brute force / credential stuffing** → `login_failure` rate spike; `auth_fail_ratio` rises sharply.
- **MFA bombing / push-fatigue** → `mfa_failure` spikes followed by one success; `mfa_fail_ratio` becomes non-zero for accounts that normally never see MFA churn.
- **Compromised credentials post-phishing** → `account_unlocked` followed by unusual `login_success` from a peer-unusual host (joined with 12_).
- **Shift workers** (typical in hospitals) have very predictable hourly hours-of-day curves; deviations are loud signal.
- **Password sprays** are detected at the *user* level here (per-target) and at the *host* level by `12_` (`distinct_src_ip` per user).

**How.**

- Aggregation primitive is `count(condition)` — counts rows where a Boolean is true. Equivalent to `SUM(CASE WHEN cond THEN 1 ELSE 0 END)`.
- Ratios are derived in-place: `if(N>0, k/N, 0)` to avoid divide-by-zero.
- These are *count features*; the unbounded count distribution motivates the **per-entity baseline** (file 07) — Z-scores on Poisson-like data are not exactly Gaussian, but for `μ ≥ 10` the normal approximation is OK; below that we lean on the q99 breach.

**Limitations.**

- Username is extracted via regex from a JSON string; entities with no `actor.username` (cards, system tasks) are silently dropped by `filter entity_id = *`.
- Same user logging in from two roles is treated as one entity (no role-aware splitting).

---

### `02_features_endpoint.pq` — Host endpoint activity, hourly

**What.** Per (host, hour), 9 features about overall host activity: total events, failures, info-level events, failure ratio, high-severity counts, and per-category breakdown (auth, data_transfer, ti_connection, card_operations).

**Why.**

- **Compromised host / lateral movement staging** → unusual mix of categories on a host (e.g., an HIS app server suddenly emitting `card_operations`).
- **Ransomware pre-cursor** → spike in `host_high_severity` events on a server that normally only hosts `data_transfer`.
- **Mis-segmentation** → a clinical workstation that *should* only do auth + data starts emitting `ti_connection` (it is sitting on the gematik network it shouldn't be).

**How.** Same `count(condition)` primitive; combines two `class_uid` filters in
one pass so total host activity is consistent across families.

**Limitations.**

- One numerator per host. A multi-tenant SaaS appliance (rare in HIS) would be misrepresented.

---

### `03_features_network.pq` — TI / Konnektor / VPN, hourly

**What.** Per (host, hour), 15 features around the German Telematik
Infrastruktur lifecycle: `ti_events`, `ti_failures`, `ti_failure_ratio`,
Konnektor connect/disconnect/health-check, **`konnektor_flap_score`**, VPN
tunnel failures/reconnects, certificate expired/expiring/valid, TI service
unavailable/available, high-severity events.

**Why.**

- **Konnektor flapping** = repeated connect / disconnect cycles → either hardware degradation (operational) or active MitM / wedge-attack against TI (security).
- **Certificate expiry** is a slow-motion incident — `cert_expiring` rising over days is a great early warning.
- **gematik availability auditing** — sum of `ti_service_unavailable` per quarter is the artefact regulators want.
- **NIS2 Art. 21(2)(h)** (cryptography) and **gematik TR-03116** (TI security) are mapped here.

**How.**

- `konnektor_flap_score = konnektor_disconnected + vpn_tunnel_failed` is a **hand-rolled composite**. It is not derived from a baseline — its absolute value is meaningful: 0 = stable, 1–2 = noise, 5+ = problem.
- Composites like this are valuable because the baseline of a *sum* of low-rate counters is more Gaussian than the baseline of a single rare event.

**Limitations.**

- `ti_service_unavailable` may overlap with `vpn_tunnel_failed` for the same root cause; we count them independently — leads to double-amplification in scoring. A weighted-event-cause-tree would fix it (improvement section §3).

---

### `04_features_cloud.pq` — Data transfer (HL7/FHIR/exports/prints), hourly, per user

**What.** Per (user, hour), 14 features on outbound data movement:
`data_transfer` events / failures, export & import (initiated, completed),
**`total_records_exported`** (sum of `details.record_count`), FHIR API requests,
HL7 received / sent, print jobs, email notifications, report generations,
external destinations.

**Why.**

- **Insider data exfiltration** is the #1 healthcare UEBA use case. A clinician
  normally prints 10 reports/day; suddenly 500 → loud signal.
- **HL7 / FHIR misuse** (e.g., scripted scraping through a FHIR API by a compromised service account) → `fhir_requests` z-score.
- **Pre-merger data theft** — staff exfiltrating patient registries before resigning is a documented pattern.
- **`total_records_exported`** is a sum, not a count, so its baseline tracks the *volume* of GDPR-relevant exports, not just the *number of clicks*.

**How.**

- The numeric `record_count` parse uses `regex=[0-9]+` (no quotes, because JSON numbers aren't quoted).
- `sum(record_count)` would 500 if combined with `if(...)`, so we extract record_count *only* via regex (it is non-null only on `DATA_EXPORT_COMPLETED`), and SDL ignores null values inside `sum`.

**Limitations.**

- Print jobs without a page-count attribute can't be sized — only counted.
- "External Specialist" destination is a string literal — fragile to spelling drift in the HIS UI. A normalisation table (`destination_class`) is suggested as improvement.

---

### `05_features_healthcare.pq` — SMC-B / HBA card operations, hourly, per host

**What.** Per (host, hour), 17 features on card lifecycle:
- card reads (success/failure)
- PIN (verified, failed, blocked, low-attempts-remaining)
- card removed, decryption, signature created, auth success/failed
- per card type: `smcb_events`, `hba_events`, `qes_pin_attempts`
- `card_failure_ratio`

**Why.**

- **gematik mandates** that PIN and card events be auditable for years (TR-03145).
- **Card cloning / forensic indicator**: card-removed within seconds of PIN entry, repeated across many cards → physical tampering at a terminal.
- **HBA misuse** (HBA = personalised practitioner card, signing key for legal QES signatures): unusual `card_signature_created` count = potential digital forgery.
- **PIN attack** is bounded by gematik to 3 attempts — `low_attempts_remaining` is a near-real-time tampering signal.
- **`qes_pin_attempts`** is broken out because QES (Qualified Electronic Signature) is what legally binds a clinician to a prescription/document; abuse here is forensic-grade.

**Why HOST not USER?** In this tenant, card events do not carry
`actor.username`. They are bound to the card and the terminal/host. So we
attribute them to the Konnektor or card-terminal host. This is correct: gematik
auditing also binds events to the terminal-id + Konnektor-serial, not to a user.

**How.** Same count-condition pattern. The post-group `filter card_events > 0`
drops hosts that contribute nothing for the hour — important because the
`ueba_features_hourly` table would otherwise carry many zero-rows for hosts
that don't have card terminals.

**Limitations.**

- We can't directly tie a card event to a clinician without an external join
  (Konnektor logs → HBA-serial → personalverwaltung). Improvement §1 proposes
  this join.

---

### `06_peers_dynamic.pq` — Dynamic peer-group construction, weekly

**What.** Defines `peer_id` for each entity.

- **Users:** `peer_id = "role=<role>|hosp=<hospital_id>"`. So "nurse @ Klinik-A" and "nurse @ Klinik-B" are different peer groups; "doctor @ Klinik-A" is a third peer group.
- **Hosts:** `peer_id = "host_fam=<hostname>|loc=<facility location>"`.

**Why.** Self-baselines (file 07) catch deviation from *your own normal*. Peer
baselines (file 08) catch *being the only one in your peer group doing X*. The
classic example: nurse Alice always exports ~20 records/hour during day-shift;
that's her normal. But her *peer group* (nurses @ same hospital) only exports
~5 records/hour. Alice's *self* baseline says "fine"; her *peer* baseline says
"highly unusual versus your colleagues". Both perspectives are needed.

**How.**

- Static peer-id assignment is fast and explainable. Documented limitation:
  small peer groups (n<10) have noisy baselines — improvement §4 suggests a
  fall-back to behavioural clustering.

**Limitations.**

- Role can be missing on card events (see file 05) — we drop those rows for the
  user-peer pass.

---

### `07_baselines_entity.pq` — Per-entity baselines, nightly

**What.** From `ueba_features_hourly` over the last 28 days, compute for each
(entity, feature):

- `μ` (mean)
- `σ` (standard deviation, sample)
- `median`, `q90`, `q99` (quantiles)
- `n` (sample count)

Keep only baselines with `n ≥ 24 × 14` (≥14 days of hourly samples). Anything
shorter is too noisy to alert on.

**Why.** This is the **self-baseline**. Z-scoring against it tells you "is this
hour weird *for this entity*?"

**How — choice of statistics.**

- **Mean + stddev** are the parametric workhorses. They assume roughly Gaussian
  shape. Hourly counts are usually right-skewed Poisson-like — for `λ ≥ 10` the
  normal approximation is OK but not perfect.
- We *also* keep **quantiles** because they are robust to outliers. `q99` is
  effectively "the upper bound of normal" — exceeding it costs +1.5 in the
  feature_score (file 09).
- Quantiles do not require any distributional assumption; they are the
  **non-parametric** safety net against heavy-tailed features (e.g., MFA
  failures: 99% of hours = 0, then one bad hour = 50).
- **Why 28 days?** Long enough to absorb weekday/weekend shape (4 full weeks);
  short enough to follow recent behaviour drift (e.g., new role, vacation
  returning).
- The 14-day threshold (`n ≥ 336`) is a **stability gate**: features with too
  few samples are not robust. If you fired alerts off a baseline of n=20 you'd
  see noise.

**Limitations.**

- No **seasonality decomposition** (weekday vs weekend, day-shift vs
  night-shift). This means a nurse who works only nights will have a baseline
  averaging in zero-activity day hours. Improvement §2 fixes this.

---

### `08_baselines_peer.pq` — Per-peer baselines, nightly

**What.** Same statistics as 07, but grouped by `peer_id` × `feature_name`.

**Why.** See 06. Peer baseline is the lateral comparison.

**How.** Joins `ueba_features_hourly` to current `ueba_peer_membership`.

**Limitations.**

- Same as 07 — no seasonality.
- Membership churn (someone changes role mid-window) gets averaged into both
  peer groups during the 28-day window. Improvement §4 proposes time-aware
  joins.

---

### `09_scoring.pq` — Hourly anomaly scoring

**What.** For each (entity, hour, feature), compute four signals and combine:

```
z_self        = (value - μ_self) / σ_self
z_peer        = (value - μ_peer) / σ_peer
over_q99      = 1 if value > q99_self else 0
over_q99_peer = 1 if value > q99_peer else 0

feature_score = max(|z_self|, |z_peer|) + 1.5·over_q99 + 1.5·over_q99_peer
```

Then per (entity, hour, family):

```
family_score        = percentile(feature_score, 95)   # 95th of all feature scores in family
family_score_100    = min(100, family_score · 10)
top_features        = top-5 feature_score with explanations packed as JSON
```

Service-account suppression: if entity is in `ueba_service_accounts` and the
score is < 6, force it to 0 (service accounts have many tiny anomalies that are
mostly harmless).

Watchlist amplification: multiply by `weight` if entity is on the watchlist.

**Why each piece.**

- `z_self`: classical Mahalanobis-style deviation; tells you how far this hour
  is from *your own normal*. The **max** of `|z_self|` and `|z_peer|` is taken
  (not the sum) because both pointing the same direction is the strongest
  signal — Bonferroni-style penalty rather than additive.
- `over_q99` is the **non-parametric kicker**: even if σ is small (and z_self
  inflates wildly), exceeding the 99th percentile is unambiguously "you've
  never done this in a month". `+1.5` is hand-tuned to roughly equal a z of 3,
  which is the canonical "3-sigma" threshold.
- Service-account suppression: scanners and integrations dominate raw counts;
  without suppression they generate constant chatter. The 6.0 cap means we
  *don't* suppress them when something genuinely extreme happens.
- Watchlist: business-driven multiplier, e.g., privileged admin accounts get
  weight=1.5; recently terminated users get 2.0 until offboarded.
- **Family-score = p95 of feature-scores** — a robust aggregation. If one
  feature explodes, p95 ≈ that feature. If three features each go to z=4, the
  p95 is still the highest of them. Sum would double-count correlated features.
- **min(100, ·10)** caps and rescales so analysts read scores on a familiar
  0–100 scale.

**Why hourly?** Because:
- HIS shift changes are hourly.
- The Konnektor / TI heartbeat cycle is ≤ 1 hour.
- Daily granularity hides the "this nurse worked at 03:00, never seen before" anomaly.

**Limitations.**

- No multivariate correlation. Two features can both jump because they are
  correlated (e.g., `login_failure` and `account_locked`) and we'd score that
  twice. PCA / Mahalanobis on a per-family covariance matrix would fix this
  (improvement §5).
- σ underestimation for low-count features: if a user's `mfa_failure` was 0 for
  28 days, σ=0 and z_self collapses to 0 — the over_q99 kicker is the only
  signal. This is intentional but brittle.

---

### `10_risk_daily.pq` — Daily entity risk with 48 h half-life decay

**What.** Per (entity, day), `score`:

```
family_daily   = p95(family_score over the day)
today_risk     = Σ_family  w_family · family_daily
decayed_yday   = yday_score · exp(-λ · 24h),  λ = ln(2) / 48h ≈ 0.01444
score          = max(today_risk, decayed_yday)
```

Family weights `w_family`:

| Family | Weight | Rationale |
|---|---|---|
| `cloud` (data transfer) | **1.4** | Highest business impact (PHI exfil) |
| `endpoint` | 1.3 | Compromise indicator |
| `auth` | 1.0 | Baseline |
| `file` | 0.9 | Common false positives |
| `network` (TI) | 0.8 | Mostly operational noise |
| `dns` | 0.7 | Aux signal |
| `web` | 0.6 | Lowest, mostly compliance |

**Why exponential decay.**

- An entity that scored 90 yesterday and 10 today: an analyst still wants to
  *see* it on the dashboard today. Without decay the queue churns daily and
  yesterday's anomalies vanish. With decay, yesterday's 90 fades over 48h.
- **Half-life of 48h** is calibrated to a typical SOC SLA: triage in two
  business days. After ~5 days the score falls below ~5 and drops off.
- `max(today, decayed_yesterday)` ensures that any *new* signal wins, but
  yesterday's stays warm. This is a **lazy max-pool with exponential forget**.

**Why p95 across the day (not sum)?**

- A user whose 03:00 hour is highly anomalous shouldn't have it diluted by 23
  normal hours of zero score.
- Sum would penalise long-running incidents twice (every hour scored).
- p95 keeps daily score close to the *worst hour* — what an analyst would
  actually care about.

**Limitations.**

- Family weights are constants — not learned from outcomes. Improvement §6
  proposes feedback-driven weight learning.

---

### `11_alerts.pq` — Alert generation with explanations

**What.** Two triggers:

| Trigger | Condition | Severity ladder |
|---|---|---|
| (a) Hourly family score | `family_score > 90` in last 2 h | `critical` >98, `high` >95, else `medium` |
| (b) Daily entity risk | `score > 70` for today | `critical` >90, `high` >80, else `medium` |

Each alert carries an `explanation` JSON with the trigger reason, the
contributing features (top_features from file 09), and baseline values. The
alert_id is deterministic (`fam-<hour>-<entity>-<family>`) so re-runs are
idempotent.

**Why two triggers.**

- (a) catches **short, sharp anomalies** — the 03:00 exfil hour.
- (b) catches **slow burns** — three medium hours over a day that no single hour
  trigger would catch.

**Why explanations.**

- A score without an explanation is not auditable. NIS2 Art. 23 (incident
  reporting) and BSI B3S Art. 5 (logging) both expect *evidence*. Packing
  μ/σ/q99 plus the feature values into the alert means the analyst can
  reproduce the math from the alert alone.

**Limitations.**

- No alert deduplication across days. Improvement §7 proposes a sliding
  suppression window.

---

### `12_distinct_count_features.pq` — Distinct-count features

**What.** Eleven distinct-count features that would normally use `dcount()` but
in SDL fail with 500 on parsed fields. We use a verified **2-stage
group-and-count** pattern:

```
parse value out of message
group by (entity, hour, value) → row per distinct value
filter nulls
group by (entity, hour) → count() = distinct count
```

Features:

| Feature | Entity | Family | Signals |
|---|---|---|---|
| `distinct_src_ip` | user | auth | account-sharing, password-spray-from-many-IPs |
| `distinct_src_host` | user | auth | lateral movement on user account |
| `host_distinct_users` | host | endpoint | unusual user fan-in to host (RDP jump-box drift) |
| `host_distinct_etypes` | host | endpoint | host behaviour broadening (compromise indicator) |
| `distinct_telematik_ids` | host | network | unusual Konnektor topology |
| `distinct_destinations` | user | cloud | exfil to many endpoints |
| `distinct_export_types` | user | cloud | format-switching exfil |
| `distinct_msg_types` | user | cloud | HL7/FHIR breadth |
| `distinct_cards` | host | healthcare | card-cycling at one terminal (cloning lab) |
| `distinct_terminals` | host | healthcare | one card moving around (theft) |
| `distinct_card_types` | host | healthcare | mixed SMC-B/HBA on a terminal that shouldn't see both |

**Why these specific ones.**

- Distinct counts are **structural** features: they detect *change of shape* of
  behaviour, not change of volume. A user who normally logs in from 1 IP and
  suddenly logs in from 5 is anomalous even if total logins are normal.

**How — the 2-stage trick.**

- SDL's `dcount(parsed_value)` 500s when nested with `timebucket` + `group`.
- The 2-stage pattern is mathematically identical (`|distinct(x)| =
  count(distinct (x))`) but is parsed without the failure mode.
- The post-`group` `filter v=*` is essential — without it, "no value" becomes a
  spurious distinct.

**Limitations.**

- Distinct counts inflate quickly with cardinality. A scanner that probes 200
  IPs/hour will have a huge `distinct_src_ip` baseline and the z-score will be
  small. The `service_accounts` table suppresses these (file 09).

---

## How the pieces compose — worked example

A nurse Alice, peer "nurse @ Klinik-Süd", is observed at 03:00:

- `login_success = 5` (normally 0 at this hour, μ=0.1 σ=0.4, q99=1)
  → `z_self ≈ 12.3`, `over_q99=1`, feature_score = 12.3 + 1.5 = **13.8**
- `distinct_src_ip = 3` (normally 1, q99=1) → `over_q99=1`, feature_score = **~3**
- `print_jobs = 80` (normally 5, σ=2, q99=15) → `z_self=37.5`, `over_q99=1`,
  feature_score = **~39**

family_score(auth) = p95([13.8, 3, ...]) ≈ 13 → ·10 = **130** capped at 100.
family_score(cloud) = p95([39, ...]) ≈ 39 → ·10 = **100**.

Daily risk = 1.0 · 100 + 1.4 · 100 = **240** (no decay, fresh).

Alert fires with explanation: top features = print_jobs (z=37.5), login_success
(z=12.3), distinct_src_ip (over_q99). Analyst opens the alert and immediately
sees the triple-coincidence.

---

# How to improve UEBA for healthcare — proposals

Below are 10 concrete improvements, ranked by expected lift.

### §1. Bind card events to clinician identity (HBA-serial → HR system)

The single biggest gap is that file 05 cannot attribute a `CARD_SIGNATURE_CREATED`
to a specific physician. Approach:

- Maintain a **lookup table** `hba_to_clinician` (HBA serial → clinician_id) refreshed nightly from the hospital's identity master.
- Use SDL **lookup() / enrich** to attach `clinician_id` at parse time.
- Promote card features to per-user — file 05 becomes both host- *and* user-scoped.

Lift: QES forgery detection becomes possible. Aligns gematik audit trail with NIS2 actor-attribution.

### §2. Seasonality decomposition (hour-of-day × day-of-week)

Today's baseline averages over all hours. A night-nurse who works only 22:00–06:00 has a baseline that is *half zero*. The fix:

- Compute baselines **per (hour_of_day, day_of_week)**: 168 cells per (entity, feature) instead of one.
- Or fit a simple additive model `value = level + hour_effect + dow_effect + noise` (STL decomposition).

Lift: ~5–10x reduction in false positives on shift workers. The single biggest analyst complaint.

### §3. Event-cause-tree collapsing for correlated features

Today `ti_service_unavailable` and `vpn_tunnel_failed` are scored independently though they share root cause. Approach:

- Define a small DAG of "if A is high then collapse B,C,D into A".
- Or use Mahalanobis distance on the family-level feature vector using the empirical covariance matrix (PCA → keep top-k components, score in the residual subspace).

Lift: 2–3x precision improvement on the network family.

### §4. Behavioural peer-groups via clustering

Static `role × hospital` peer-ids are coarse. Better:

- Build a per-user **behavioural fingerprint** = vector of weekly-aggregated feature means.
- Cluster (k-means or DBSCAN) → assign cluster ID as `peer_id`.
- Refresh weekly. Add temporal smoothing so cluster IDs don't flap.

Lift: catches the "doctor-who-acts-like-a-billing-clerk" persona, which static peers miss.

### §5. Multivariate scoring (Mahalanobis or isolation forest)

Current scoring max-pools univariate z-scores. A multivariate model would catch *jointly* unusual but individually normal feature combinations:

- Per-family empirical covariance Σ from baseline window.
- Mahalanobis distance `d² = (x-μ)ᵀ Σ⁻¹ (x-μ)`.
- Or Isolation Forest run weekly on the 28-day feature matrix; current hour scored as anomaly_score.

Lift: detects the "5 small things at the same time" attack — currently invisible.

### §6. Feedback-driven family-weight learning

Family weights are constants. With analyst dispositions (`tp/fp/closed`), we can:

- Logistic regression on `family_score` → P(true positive).
- Use the fitted coefficients as new family weights.
- Retrain monthly.

Lift: precision improves with operator usage; the system gets better the more it's used.

### §7. Alert deduplication & burst suppression

Today the same anomaly can fire `fam-` alert + `risk-` alert + repeat tomorrow. Suggested suppression:

- For each entity, keep the highest-severity alert in a 24 h window; bump severity instead of creating new ones.
- Surface "alert continued — score now X" updates instead of new tickets.

Lift: ~3–5x reduction in alert queue volume.

### §8. Add four healthcare-specific feature families

- **Patient-record-access pattern** (per user, per hour): distinct patients touched, ratio of "viewed but not edited", off-hours access — these are the highest-precision exfil signals in healthcare.
- **Prescription / medication patterns** for clinicians (volume, recurrent vs new patients).
- **Telematik-cross-hospital activity** (a Konnektor in Klinik-A talking to a TI service typically used by Klinik-B = compromise indicator).
- **Print queue analytics** — print jobs to printers outside the user's department.

Lift: opens entirely new detection surface. Most of these features are easy to add (extend `04_features_cloud.pq` and `05_features_healthcare.pq`).

### §9. Threat-actor playbook overlays

Map known healthcare-ransomware playbooks (LockBit-Black, Akira) to feature combinations:

- "INTRUSION_DETECTED on host X within 6 h of unusual `host_distinct_users` on X" → +30 score.
- "DATA_EXPORT_INITIATED by user Y within 1 h of MALWARE_DETECTED on Y's workstation" → +50 score.

These are *deterministic* boosts — easy to write, easy to explain, complementary to statistical UEBA.

### §10. Clinical-context awareness

Tie UEBA into clinical workflows:

- During emergency events (mass-casualty incident), expect EMERGENCY_ACCESS_OVERRIDE spikes — auto-mute auth + cloud families for the affected facility for 4 h.
- During OR / radiology high-volume shifts, expand baselines.
- Quiet-hours suppression for paediatric departments (genuinely quiet) vs ED (genuinely never quiet).

Lift: removes the bulk of "operational" noise that frustrates SOC teams in hospitals. Requires a small **calendar table** of clinical events.

---

## Roadmap (priority order)

| # | Improvement | Effort | Lift |
|---|---|---|---|
| 1 | Card → clinician join | S | High (compliance + detection) |
| 2 | Seasonality (hour × DoW) | M | Very high (FP reduction) |
| 7 | Alert deduplication | S | High (analyst time) |
| 8 | Healthcare-specific families | M | Very high (new surface) |
| 4 | Behavioural peer clustering | M | Medium |
| 9 | Threat-actor playbook overlays | S | Medium |
| 10 | Clinical-context awareness | M | High (FP reduction) |
| 5 | Multivariate scoring | L | High (precision) |
| 6 | Feedback-driven weights | M | Compounding |
| 3 | Event-cause-tree collapsing | M | Medium |

S = ≤1 sprint, M = 2–4 sprints, L = quarter-scale.

---

## References

- Chandola, Banerjee, Kumar — *Anomaly Detection: A Survey* (ACM CSUR 2009)
- Goldstein, Uchida — *Comparative Evaluation of Anomaly Detection Algorithms* (PLoS ONE 2016)
- BSI — *B3S "Medizinische Versorgung" v1.2* — sector-specific log/audit requirements
- gematik — TR-03116 / TR-03145 — TI security and card-handling auditability
- ENISA — *NIS2 Implementation Guide for the Health Sector* (2024)
- OCSF v1.3.0 — schema for class_uid mapping (3002/3001/4001 used here)
