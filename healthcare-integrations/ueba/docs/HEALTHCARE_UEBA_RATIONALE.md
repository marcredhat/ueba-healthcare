# Why these UEBA features matter for healthcare

This document explains the security rationale behind every feature
family, every aggregation, and every alert produced by the
pipeline. 

It maps each technical artifact to a real-world threat
scenario in a hospital, clinic, medical care center (MVZ), KIM (Communication in Medicine) connector site, or other
TI-connected (Telematics Infrastructure) healthcare environment.

(
KIM stands for Communication in Medicine within the Telematics Infrastructure (TI). The service enables secure communication via e-mail. eDoctor's letters, eAU, and other medical documents can be easily exchanged between all players (TI participants) in the German healthcare system using KIM. 
Source: https://www.arvato-systems.com/industries/healthcare-pharma/kim-communication-in-medicine

The telematics infrastructure (TI) is intended to enable secure networking of medical care within Germany. The connection of all doctors' practices and hospitals ensures that medical documents can be sent to the treating doctors quickly and easily -- and especially in a secure way. This should avoid multiple examinations and make the health system more efficient.
Source: https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/E-Health/Telematikinfrastruktur/telematikinfrastruktur_node.html
)

The pipeline is statistical and unsupervised: per-entity baselines
(28-day rolling) capture what is **normal for this user / host /
service account**, peer-group baselines capture what is **normal for
similar entities**, and the hourly scoring layer surfaces what is
**unusual in both dimensions simultaneously**. Hospitals run on
highly repetitive workflows — exactly the conditions UEBA is built for.

---

## 1. Domain context

Healthcare environments are uniquely sensitive for three reasons:

1. **Patient safety**. Disruption of authentication, identity card
   readers, KIM messaging, or PVS/HIS access translates directly to
   inability to treat patients. Ransomware downtime is measured in
   *days of cancelled surgeries*, not lost revenue.
2. **High-value, high-regulation data**. ePA records, Arztbriefe,
   prescriptions, billing claims, lab results — combinations of PHI
   and PII that attract both criminal exfiltration (selling on dark
   markets) and state-sponsored espionage (research data, vaccine
   IP).
3. **Highly regular workflows**. A nurse on a Med-Surg ward logs in
   at 06:30, swipes 80 cards/day, accesses 30 patient records on her
   own ward. A KIM connector exchanges ~5 messages/hour during
   business hours. A radiology workstation prints 6 reports/day.
   These signatures are extraordinarily stable — anomalies pop.

Statistical UEBA exploits this regularity. Every feature in the
pipeline below is anchored to a real attacker behavior that
**violates the workflow pattern**, not an IOC.

---

## 2. The five feature families

The pipeline produces six output families written to
`config://datatables/ueba_features_hourly`. Each row is `(entity_type,
entity_id, hour_ts, family, feature_name, value)`. Six families
collectively cover the OWASP / MITRE ATT&CK + healthcare-specific
attack surface.

### 2.1 `auth` (15 features) → `01_features_auth.pq`

**Entity**: user. **Source**: OCSF `class_uid = 3002` (authentication events).

| Feature | Healthcare threat it surfaces |
|---|---|
| `auth_total` | Sudden spike: account takeover, brute force, automation abuse |
| `auth_fail` | Password spraying, lateral-movement reconnaissance |
| `auth_succ` | Baseline; used to compute ratios |
| `auth_fail_ratio` | Compromised credentials being tested across systems |
| `login_success` | Normal weekday-vs-weekend; **off-hours = privileged misuse** |
| `login_failure` | Brute force; account lockout attempts targeting clinicians |
| `logout` | Failure to log out = card-left-in-reader, tailgating risk |
| `session_timeout` | Implant / scheduled-task behavior abandoning sessions |
| `mfa_success` | Healthy baseline for MFA-protected accounts |
| `mfa_failure` | MFA fatigue attacks; bypass attempts |
| `mfa_fail_ratio` | High ratio = adversary repeatedly pushing prompts |
| `password_change` | Forced reset after suspected compromise — useful as signal |
| `password_reset_req` | Help-desk social engineering precursor |
| `account_locked` | Brute force already in progress |
| `account_unlocked_fail` | Stuffing attempt against locked accounts |

**Why hourly?** Hospital shifts change every 6–12 hours. Daily
aggregates blur the morning rush vs. night shift; hourly preserves
the diurnal pattern that makes anomalies stand out.

### 2.2 `endpoint` (9 features) → `02_features_endpoint.pq`

**Entity**: host. **Source**: OCSF `class_uid = 4001` (endpoint events) + auth volume from class 3002 + healthcare-app events.

| Feature | Healthcare threat it surfaces |
|---|---|
| `host_events` | Total host activity; spike = process injection / mass file ops |
| `host_failures` | Failed operations; ransomware probes for file shares |
| `host_failure_ratio` | High ratio while overall activity rises = encryption-in-progress |
| `host_high_severity` | Aggregated high-severity event count per host |
| `host_infos` | Info-level events; counts for normalization |
| `host_auth_events` | How many auth events originate from this host |
| `host_card_events` | Card-reader activity per host (a workstation w/o card reader spiking = misuse) |
| `host_data_events` | Data-classified events touching this host |
| `host_ti_events` | TI-konnektor traffic per host |

**Healthcare-specific insight**: A workstation in a clinic typically
shows tight `host_events` distributions because the same clinician
does the same workflow daily. Ransomware staging on that host
typically multiplies `host_events` 5–10× — easy to detect with z-score.

### 2.3 `network` (15 features) → `03_features_network.pq`

**Entity**: TI-konnektor / network service. **Source**: TI
(Telematikinfrastruktur) connector logs + VPN + certificate events.

Healthcare-specific because the TI-konnektor is the regulated gateway
between the practice and the German national healthcare exchange. Its
availability and integrity is a regulatory obligation (gematik
Sicherheitsanforderungen).

| Feature | Healthcare threat it surfaces |
|---|---|
| `konnektor_health_check` | Baseline pings; absence = konnektor offline (patient-safety) |
| `konnektor_connected` | Healthy session counts |
| `konnektor_disconnected` | Disconnect events; spike = misconfiguration or DoS |
| `konnektor_flap_score` | Repeated flapping = unstable physical/network connection |
| `vpn_tunnel_reconnect` | Normal flap rate; high rate = attacker holding session open |
| `vpn_tunnel_failed` | Brute-force VPN auth; misconfigured client |
| `cert_valid` | Healthy certificate lifecycle |
| `cert_expiring` | 30-day warning; risk of service interruption |
| `cert_expired` | **Patient-safety incident**: konnektor cannot send eRezepte |
| `ti_events` | TI message volume; spike could indicate exfiltration via KIM |
| `ti_failures` | Failed TI sends; high = misconfiguration or downstream DoS |
| `ti_failure_ratio` | Compares to normal failure rate per practice |
| `ti_service_available` | Service-availability heartbeats |
| `ti_service_unavailable` | Counts of unavailability; chronic = vendor escalation |
| `high_sev_events` | High-severity network events; lateral-movement detection |

### 2.4 `cloud` (14 features) → `04_features_cloud.pq`

**Entity**: user. **Source**: PVS/HIS/ePA application logs — record
imports/exports, FHIR API calls, HL7 traffic, printing, email
notifications.

These features capture **bulk data movement**: the classic exfiltration
signature when a clinician's account is compromised or a rogue insider
exports records.

| Feature | Healthcare threat it surfaces |
|---|---|
| `export_initiated` | Each export event — baseline is 0-2/day for most users |
| `export_completed` | Successful completion; mismatch with initiated = aborted ops |
| `total_records_exported` | Aggregate volume — flag exports >> p99 |
| `external_destinations` | Number of distinct external targets |
| `import_initiated` / `import_completed` | Inbound data; insider data poisoning |
| `print_jobs` | Mass printing of patient records = exfil via physical channel |
| `email_notifications` | Spike = social-engineering pretext or data-leak via email |
| `hl7_sent` / `hl7_received` | HL7 message volumes; data-channel anomalies |
| `fhir_requests` | FHIR API calls; bulk API exfiltration |
| `dt_events` | DICOM / imaging traffic; radiology study exfil |
| `dt_failures` | Failed DICOM ops; reconnaissance |
| `report_generated` | Lab/imaging reports — bulk generation outside normal hours |

**Why "cloud"?** It's the cloud-style application layer of healthcare
IT (PVS, HIS, ePA, FHIR-on-FHIR). Naming is loose; the family
captures application-layer record movement.

### 2.5 `healthcare` (17 features) → `05_features_healthcare.pq`

**Entity**: user. **Source**: SMC-B (institution card), HBA
(Heilberufsausweis, professional ID card), eGK (patient card)
events, plus PIN / qualified electronic signature (QES) operations.

**This is the family that does not exist in generic UEBA products.**
It captures attacker behavior specific to the German telematics card
infrastructure.

| Feature | Healthcare threat it surfaces |
|---|---|
| `card_events` | Baseline card traffic per professional |
| `card_failures` | Failed card operations |
| `card_failure_ratio` | High ratio = card-reader tampering, card cloning attempt |
| `card_read_success` / `card_read_failure` | Physical-layer card-reader health |
| `card_auth_success` / `card_auth_failed` | Card-based auth; failed = PIN unknown / stolen card |
| `card_pin_verified` | Baseline PIN-OK events |
| `card_pin_failed` | Failed PIN attempts on a single card — pre-blocking signal |
| `card_pin_blocked` | Card locked due to repeated PIN failures |
| `card_removed` | Each card removal — pulling card during operation = bypass attempt |
| `card_signature_created` | Each qualified e-signature — anomalies on these are *legally significant* (signed documents) |
| `card_decryption` | Decryption operations on the card; sudden spikes = bulk record access |
| `hba_events` | Professional ID card events; misuse of clinician identity |
| `smcb_events` | Institution card events; impersonating the practice |
| `low_attempts_remaining` | Card has ≤1 PIN attempt left — likely brute force in progress |
| `qes_pin_attempts` | QES PIN attempts; usually 1-2/day, sudden 10+ = breach |

### 2.6 `distinct counts` (11 features) → `12_distinct_count_features.pq`

**Why these are special**: SDL's `dcount()` returns HTTP 500 on
parse-extracted fields on this tenant, so we emulate it with a
two-stage `| group` (inner group dedups, outer group counts). These
features capture **breadth of activity**, which is often the strongest
attack signal.

| Feature | What unusual breadth means |
|---|---|
| `distinct_cards` (per user/hour) | Normal: 1. Sharing/loaning card. >1 = audit |
| `distinct_terminals` (per user/hour) | Normal: 1-2. Many = card cloning or tailgating |
| `distinct_card_types` | Single user using HBA + SMC-B + eGK in same hour = misuse |
| `distinct_telematik_ids` | One user touching many institution IDs = lateral movement |
| `distinct_src_ip` (per user/hour) | User logging in from multiple IPs in the same hour |
| `distinct_src_host` | Multiple hosts running as same user |
| `host_distinct_users` | One host servicing many distinct users in an hour — kiosk vs. compromise |
| `host_distinct_etypes` | High event-type diversity on one host = post-exploit recon |
| `distinct_destinations` | Bulk export to many destinations = exfiltration |
| `distinct_export_types` | Touching all export formats simultaneously = data hoovering |
| `distinct_msg_types` | TI/HL7 message-type diversity; unusual = reconnaissance |

---

## 3. Peer-grouped detection: not all clinicians are alike

`06_peers_dynamic.pq`
clusters entities into dynamic peer groups based on **observed
behavior**, not org-chart attributes. Two clinicians in the same role
who never touch the same systems are not actually peers.

The script computes per-user signatures
(`avg_card_events`, `avg_auth_events`, `avg_export_events`,
`role_signature_hash`) over 30 days and groups users with similar
signatures into one peer ID. The hash bucketing means peers form
**automatically**, without explicit role assignment from HR.

**Healthcare benefit**: a billing-office user who suddenly displays
clinician-like card and PVS activity will diverge sharply from her
own peer group, even if her individual baseline hasn't shifted much
yet.

---

## 4. The two-baseline architecture

`07_baselines_entity.pq`
computes per-entity stats over the last 28 days (excluding the most
recent 1 day, to prevent contamination):

- `mu` = mean
- `sigma` = std-dev
- `median`, `p90`, `p99`
- `n` = sample count (must be ≥ 336 hourly samples ≈ 14 days)

`08_baselines_peer.pq`
computes the same statistics over the entity's peer group.

For each (entity, feature) at each hour we compute **both**:

- `z_self = (value - mu) / sigma`
- `z_peer = (value - mu_peer) / sigma_peer`

Anomalous behavior shows up as **both unusual for this entity and
unusual for their peers**. Either signal alone has high false-positive
rates in healthcare:

- Self alone: a new clinician with thin history triggers constantly
- Peer alone: a senior consultant who legitimately has elevated
  privileges always shows up as a "peer outlier"

The pipeline scores `feature_score = max(|z_self|, |z_peer|) + 1.5·over_q99 + 1.5·over_q99_peer`,
giving a strong boost when the value exceeds the p99 threshold in
either dimension. See
`09_scoring.pq`.

---

## 5. Family rollup and risk decay

`09b_family_scores.pq`
collapses per-feature scores to per-family p95s, then
`10_risk_daily.pq`
computes a weighted daily risk score:

```
score(entity, day) = max(
    sum_family( weight(family) × p95(family_score) ),
    yday_score × exp(-ln 2 / 48 × 24)   ≈ yday × 0.7071
)
```

**Weights**:

| Family | Weight | Healthcare rationale |
|---|---|---|
| `healthcare` | 1.5 | Card/QES misuse has direct patient-safety + legal impact |
| `cloud` | 1.4 | PVS/HIS exfiltration is direct PHI exposure |
| `endpoint` | 1.3 | Endpoint compromise enables everything else |
| `auth` | 1.0 | Baseline; many false positives at low weights |
| `file` | 0.9 | Generic file ops, lower signal density |
| `network` | 0.8 | TI/VPN noise rate is high |
| `dns` | 0.7 | DNS is generally noisy without specific indicators |
| `web` | 0.6 | Web is the noisiest layer in healthcare |

**The exponential decay** (half-life 48h) ensures that an entity
remains "warm" for a day or two after a spike, so a stealthy attack
unfolding over multiple days still raises risk even on hours where the
attacker is quiet.

---

## 6. Alert generation

`11_alerts.pq`
produces two alert types into `ueba_alerts`:

1. **Sustained anomaly**: any single feature scores > 3.0 for ≥ 3 of
   the last 6 hours
2. **Composite anomaly**: ≥ 3 distinct features all > 2.0 in the same
   hour (the "many small anomalies" signal that single-feature
   detection misses)

Both forms are tuned to **patient-safety latency** — alerts within an
hour, not a day. A nurse logging in from a strange IP at 02:17 should
trigger by 03:17, before the night shift hands over.

---

## 7. Threat-hunting use cases

Concrete attacker scenarios this pipeline detects, mapped to features:

### 7.1 Compromised clinician credentials (account takeover)
- `auth.auth_fail_ratio` z-score spike during off-hours
- `cloud.external_destinations` distinct count rises
- `cloud.total_records_exported` exceeds p99
- → composite alert within 1-2 hours

### 7.2 Insider data exfiltration via PVS
- `cloud.export_initiated` over peer-group p99
- `cloud.distinct_destinations` rising
- `cloud.print_jobs` rising
- `endpoint.host_distinct_etypes` (unusual breadth of activity)
- → sustained alert + manual review

### 7.3 Stolen HBA / SMC-B card
- `healthcare.card_pin_failed` z-score spike (PIN unknown to thief)
- `healthcare.distinct_terminals` rising (thief moves around)
- `healthcare.card_pin_blocked` event
- → composite alert immediately on first PIN failure burst

### 7.4 TI-konnektor compromise / supply-chain
- `network.cert_expired` event despite normal traffic
- `network.konnektor_flap_score` rising
- `network.ti_failure_ratio` rising
- → sustained alert on availability metrics

### 7.5 Ransomware staging on workstation
- `endpoint.host_events` z-score spike
- `endpoint.host_failures` rising
- `endpoint.host_failure_ratio` rising
- `endpoint.host_distinct_etypes` rising (process diversity = recon)
- → composite alert, often hours before encryption begins

### 7.6 Card cloning at terminal
- `healthcare.distinct_cards` rising at a single terminal
- `healthcare.card_read_failure` rising
- `healthcare.distinct_card_types` rising
- → sustained alert on the terminal entity

### 7.7 KIM message tampering / bulk send abuse
- `cloud.hl7_sent` z-score spike
- `network.ti_events` over peer p99
- `network.ti_failure_ratio` rising (downstream rejection)
- → composite alert

---

## 8. Operational benefits

- **Self-tuning**: 28-day rolling baselines automatically adjust to
  seasonality, staffing changes, vacation periods
- **No signature maintenance**: zero IOCs to update — this scales
  across hundreds of clinic sites without analyst overhead
- **Explainable**: every score is `(value, mu, sigma, z_self, z_peer,
  q99)` — analysts can verify *why* a score is high
- **Per-feature attribution**: alerts cite the specific feature(s)
  that drove the score, so triage is fast (`"this user fired on
  auth.auth_fail_ratio and cloud.external_destinations"`)
- **Latency under 1 hour** from event → alert
- **Healthcare-specific coverage** of card / KIM / TI that generic
  UEBA misses entirely

---

## 9. Limitations and tuning

- **Cold-start**: needs ≥ 14 days of history (336 hourly samples) per
  feature before scoring. New clinicians, new hosts, and new
  install sites need a 2-week warm-up.
- **Behavioral drift**: legitimate workflow changes (new EHR module,
  ward reorganization) cause transient false positives until the
  baseline catches up (~7 days at the new normal).
- **Peer group quality**: dynamic peer groups depend on having enough
  similar users. A 5-person clinic has noisier peer baselines than a
  500-bed hospital.
- **The p99 boost** in scoring deliberately overweights extreme
  events to compensate for the natural fat tails of healthcare
  data (sometimes a clinician really does print 200 documents in an
  hour for legitimate research) — tune the `1.5×` coefficient down
  for higher precision, up for higher recall.
