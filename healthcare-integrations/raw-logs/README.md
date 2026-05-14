# Raw Log Files for Observo → AI SIEM (OTLP HTTP)

This folder contains realistic raw log files for the two healthcare sources
(Avelios Medical HIS and Omniconnect TI Gateway) ready to drop into an
S3-compatible bucket and pull into AI SIEM through Observo Data Pipelines
over OTLP HTTP.

## Files

```
raw-logs/
├── avelios-medical.ndjson                         # flat NDJSON, 1000 events / 24h
├── omniconnect.ndjson                             # flat NDJSON, 1000 events / 24h
├── avelios-medical/<YYYY>/<MM>/<DD>/
│   └── avelios-medical.YYYY-MM-DD-HH.ndjson.gz    # 25 hourly-rotated, gzipped files
├── omniconnect/<YYYY>/<MM>/<DD>/
│   └── omniconnect.YYYY-MM-DD-HH.ndjson.gz        # 25 hourly-rotated, gzipped files
└── generate_rotated_logs.py                       # regenerate at any time
```

Format: **NDJSON** — one JSON event per line, UTF-8.
Each event already carries `timestamp`, `event_category`, `event_type`,
`severity` and source-specific OCSF-mappable fields (see top-level README).

## S3 layout

The hourly-rotated tree mimics the most common log-shipper output (CloudTrail-
style). Drop it as-is into a bucket prefix:

```
s3://my-bucket/healthcare/avelios-medical/2026/05/08/avelios-medical.2026-05-08-12.ndjson.gz
s3://my-bucket/healthcare/omniconnect/2026/05/08/omniconnect.2026-05-08-12.ndjson.gz
```

For MinIO / Ceph / R2 / GCS-S3-shim the keys are identical.

## Observo pipeline — S3 → OTLP HTTP → AI SIEM

### 1. Source: S3
| Field | Value |
|---|---|
| Type | **S3 / S3-compatible** |
| Bucket | `my-bucket` |
| Prefix | `healthcare/avelios-medical/` (one source per pipeline) |
| File format | **NDJSON** (auto-gunzip on `.gz`) |
| Polling | New objects via SQS / event notification (or scheduled scan) |

Repeat for `healthcare/omniconnect/`.

### 2. Processor: light enrichment (optional)
Observo can flatten nested objects and add static fields. Recommended:

```yaml
- type: add_fields
  fields:
    serverHost: avelios-medical          # or omniconnect
    parser:     Avelios-Medical-OCSF     # or Omniconnect-OCSF
    logfile:    avelios-medical.ndjson   # or omniconnect.ndjson
```

These three fields drive parser routing in SDL — they match exactly what
`deploy_and_ingest.py` sets via `addEvents.sessionInfo`.

### 3. Destination: OTLP HTTP → SentinelOne AI SIEM

| Field | Value |
|---|---|
| Destination type | **OpenTelemetry (OTLP/HTTP)** |
| Endpoint | `https://xdr.us1.sentinelone.net/services/otlp/v1/logs` |
| Authentication | Bearer token (Log Write key) |
| Header | `Authorization: Bearer <SDL_LOG_WRITE_KEY>` |
| Compression | `gzip` |
| Body format | OTLP `ResourceLogs` |

Map the Observo event into the OTLP `LogRecord`:

| OTLP field | Source field |
|---|---|
| `body` | the entire JSON event (stringified) |
| `time_unix_nano` | `timestamp` (ISO-8601 → ns) |
| `severity_text` | `severity` |
| `attributes["serverHost"]` | static `avelios-medical` / `omniconnect` |
| `attributes["parser"]` | static `Avelios-Medical-OCSF` / `Omniconnect-OCSF` |
| `attributes["logfile"]` | static log file name |
| `resource.attributes["service.name"]` | `Avelios Medical` / `Omniconnect` |
| `resource.attributes["service.namespace"]` | `healthcare` |

Once delivered, the events arrive on SDL with the right `serverHost`/`parser`
attributes and are picked up by the `Avelios-Medical-OCSF` /
`Omniconnect-OCSF` parsers deployed by `deploy_and_ingest.py`.

### 4. Verify in AI SIEM

```
serverHost='avelios-medical' or serverHost='omniconnect'
| group ct=count() by serverHost, event_category | sort -ct
```

## Regenerating

```bash
# Flat NDJSON files (one per source)
python3 ../avelios-medical/sample-data/generate_avelios_events.py \
    --count 1000 --hours 24 --format ndjson \
    --output avelios-medical.ndjson

python3 ../omniconnect/sample-data/generate_omniconnect_events.py \
    --count 1000 --hours 24 --format ndjson \
    --output omniconnect.ndjson

# Hourly-rotated, gzipped tree
python3 generate_rotated_logs.py
```

## Privacy

All identifiers (KVNR, BSNR, LANR, Telematik-IDs, ICCSN, patient IDs, user
names) are **synthetic, randomly generated** and do not reference real
patients, clinicians, insurances, hospitals, or healthcare facilities.
Safe to commit and share.
