# Healthcare Integrations for SentinelOne AI SIEM (BSI / NIS2)

End-to-end pipeline that ingests sample data for two healthcare platforms,
parses it into OCSF v1.3.0, and visualizes BSI- / NIS2-relevant compliance
findings in a tabbed SDL dashboard.

- **Avelios Medical** — modular hospital information platform (HIS)
- **Omniconnect** — software interface securing HIS ↔ German Telematics
  Infrastructure (TI) traffic (Konnektor, eGK, HBA, SMC-B, eRezept, ePA,
  KIM, VSDM)

## Directory layout

```
healthcare-integrations/
├── README.md
├── deploy_and_ingest.py          # 1-shot: deploy parsers + ingest events + verify
├── verify_ingestion.py           # standalone PowerQuery verification report
├── avelios-medical/
│   ├── sample-data/generate_avelios_events.py
│   └── parsers/avelios-medical.conf       (Scalyr/SDL parser, OCSF v1.3.0)
├── omniconnect/
│   ├── sample-data/generate_omniconnect_events.py
│   └── parsers/omniconnect.conf           (Scalyr/SDL parser, OCSF v1.3.0)
├── dashboards/
│   └── deploy_dashboards.py      # deploys /dashboards/bsi-nis2-healthcare-overview
├── ueba/                          # SDL PowerQuery UEBA pack (files 01..12)
│   ├── 00_datatables_schema.md
│   ├── 01..12_*.pq               # feature extractors, baselines, scoring, alerts
│   ├── README.md                  # operator guide
│   ├── SDL_POWERQUERY_QUIRKS.md
│   └── FEATURE_EXTRACTORS_EXPLAINED.md   # scientific documentation + roadmap
├── docs/
│   ├── german-healthcare-ma-observo-use-cases.md
│   └── observo-demo-outline.md
└── raw-logs/                      # S3-style NDJSON.gz + Observo OTLP setup
```

All scripts read SDL credentials from
`shared/sentinelone-sdl-api/config.json` via the shared `SDLClient`.

## Quick start

```bash
# 1. Deploy parsers + ingest 100 sample events per source + verify OCSF coverage
python3 deploy_and_ingest.py --count 100 --hours 24

# 2. Run a wider verification report (events are backdated up to 24h)
python3 verify_ingestion.py 24h

# 3. Deploy the BSI / NIS2 dashboard
python3 dashboards/deploy_dashboards.py
```

After step 3, open in AI SIEM:
**Visibility Enhanced → Dashboards → BSI / NIS2 healthcare compliance**
or directly: `https://<your-tenant>.sentinelone.net/#/dashboards/bsi-nis2-healthcare-overview`

## What gets deployed

| Object | SDL path | Purpose |
|---|---|---|
| Parser | `/logParsers/Avelios-Medical-OCSF` | JSON → OCSF for Avelios HIS events |
| Parser | `/logParsers/Omniconnect-OCSF` | JSON → OCSF for Omniconnect TI events |
| Dashboard | `/dashboards/bsi-nis2-healthcare-overview` | 4-tab BSI/NIS2 compliance overview |

### Dashboard tabs

1. **Overview** — totals, severity mix, OCSF class breakdown, recent HIGH/CRITICAL.
2. **Avelios HIS** — PHI access (GDPR Art. 32), authentication, admin changes.
3. **Omniconnect** — Konnektor/TI health, card ops, eRezept, ePA, KIM, VSDM.
4. **Compliance** — control mapping table:

| Control | BSI / NIS2 ref | Evidence |
|---|---|---|
| Identity & Access | BSI ORP.4 / NIS2 21(2)(i) | `event_category in (authentication, card_operations)` |
| Logging & Audit | BSI OPS.1.1 / NIS2 21(2)(b) | All ingested events |
| Cryptography | BSI CON.1 / NIS2 21(2)(h) | `event_type contains CERTIFICATE/ENCRYPTION/SIGNATURE` |
| Incident Detection | BSI DER.1 / NIS2 21(2)(c) | `category_uid=2` |
| Data Protection | BSI CON.3 / GDPR Art. 32 | `event_category=patient_access OR epa` |
| Supply Chain (TI) | BSI TR-03116 / NIS2 21(2)(d) | `event_category=ti_connection` |

## Event categories generated

**Avelios Medical** — `authentication`, `patient_access`, `administrative`,
`data_transfer`, `security`, `system`.

**Omniconnect** — `ti_connection`, `card_operations` (eGK/HBA/SMC-B),
`vsdm`, `erezept`, `epa`, `kim`, `security`, `system`.

## Sample PowerQueries

```powerquery
serverHost='avelios-medical' or serverHost='omniconnect'
| group ct=count() by serverHost, event_category, class_name | sort -ct

serverHost='avelios-medical' event_category='patient_access'
| group ct=count() by event_type | sort -ct

serverHost='omniconnect' (event_type contains 'CERTIFICATE' or event_type contains 'ENCRYPTION')
outcome!='success'
| columns timestamp, event_type, severity_str | sort -timestamp
```

## Dashboard authoring rules followed

Built per the
[`sentinelone-sdl-dashboard` skill](https://github.com/pmoses-s1/claude-skills/tree/main/sentinelone-sdl-dashboard):

- Explicit `{w,h,x,y}` layout on a 60-wide grid via a `Grid` helper.
- Markdown panels use `markdown` (never `content`).
- Number panels end in `| limit 1`.
- Donut/pie queries return exactly 1 text + 1 numeric column.
- CAS-guarded deploy: `get_file → put_file(expected_version) → re-fetch → canary check`.
- Path: `/dashboards/<name>` (never `/dashboard/<name>`).
