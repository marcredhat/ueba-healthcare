# Developer-Workstation UEBA Kit (SentinelOne SDL)

End-to-end synthetic UEBA dataset + parser + hunt library for a
"developer workstation" data source. Every hunt is validated against
the synthetic events.

## Layout

| Path | Purpose |
|------|---------|
| `sample-data/generate_devworkstation_events.py` | Synthesizes ~24h of dev-workstation telemetry (PROCESS_START, FILE_CREATE/READ/WRITE, DNS_QUERY, REGISTRY_SET) with embedded benign + malicious scenarios. |
| `parsers/developer-workstation.conf` | Scalyr/SDL parser config. Maps the JSON event shape into flattened OCSF-friendly columns (`process.image_name`, `dns.query`, `file.path`, ...). |
| `hunts_devworkstation.py` | Self-contained hunt runner. Executes the 18 hunts (`--hunt H1`..`H18`, or all) via the SDL PowerQuery API. |
| `create_npm_typosquats_dataset.py` | One-shot creator of the `npm_typosquats` lookup table (both putFile + savelookup) used by H15. |
| `HUNT_MAPPING.md` | Scenario → hunt-ID cross-reference. |
| `probe_*.py`, `verify_*.py`, `test_*.py` | Diagnostic / verification harnesses kept as reference for how each hunt was validated and tuned against this tenant. |

## Prerequisites

- A SentinelOne tenant with PowerQuery + datatable APIs (Singularity XDR / Scalyr).
- A `sentinelone-sdl-api/` sibling directory containing:
  - `config.json` with at minimum `base_url` and `console_api_token`
  - `scripts/sdl_client.py` (a thin requests-based wrapper)

By default every script looks for
`../../sentinelone-sdl-api/config.json` relative to its own location.
Override with `SDL_API_DIR=/absolute/path`.

## Quick start

```bash
# 1. Generate + ingest synthetic events (assumes a deploy_and_ingest.py orchestrator
#    is wired up; otherwise call generate_devworkstation_events.py directly and
#    upload via the SDL uploadLogs endpoint).

# 2. Create the npm_typosquats lookup once (idempotent).
python3 create_npm_typosquats_dataset.py

# 3. Run all 18 hunts.
python3 hunts_devworkstation.py --start 24h

# 4. Or run a single hunt with full output:
python3 hunts_devworkstation.py --hunt H15 --start 24h

# 5. Print a hunt query without running it:
python3 hunts_devworkstation.py --hunt H8 --print-only
```

## Tenant-specific notes baked into the queries

Several hunts were re-tuned for the quirks of the SDL tenant they target.
Notable patches retained in `hunts_devworkstation.py`:

| Hunt | Tuning |
|------|--------|
| **H2** | `file.content` is stored with JSON-escaped quotes. The regex matches the *bare* permission keywords (`<all_urls>`, `webRequestBlocking`, ...) — quoted-token forms never match. |
| **H8** | `process.parent.start_time` is not emitted. The time-window guard is dropped; the (IDE parent) + `--folder-uri` parse + shell child trio is itself the correlation signal. |
| **H14** | Must gate on `event_type = "DNS_QUERY"` and use `dns.query matches ".+"` instead of `= *`. The malicious-node parent set is broadened to include IDE process names. |
| **H15** | Uses the `join ... | dataset` form (not `lookup ... from`). The UI's `lookup` resolver requires `savelookup` registration and is finicky across tenant scopes; `dataset` is a stable file-path reference. Query is marked `raw=True` so the runner does not auto-prepend `serverHost`. |
| **H16** | Logic inverted: flag any internal-scope (`@your-org/*`) install that does **not** carry a `--registry=https?://` override. |
| **H18** | `image_name` list broadened to include `.exe` / `.cmd` variants. |

## Hunt index

| ID | Title |
|----|-------|
| H1 | Suspicious VS Code / Cursor / Windsurf extension paths |
| H2 | Extensions requesting dangerous permissions |
| H3 | Sideloaded (non-Web Store) extensions |
| H4 | Native messaging host registration |
| H5 | IDE Marketplace UI launched outside the browser |
| H6 | `code --install-extension <local-path>` |
| H7 | IDE spawns suspicious shell (curl|sh, certutil) |
| H8 | Workspace-trust auto-run of tasks |
| H9 | IDE accessing credential stores |
| H10 | Code OAuth code grant URLs in IDE traffic |
| H11 | npm/yarn lifecycle hook abuse (preinstall, postinstall) |
| H12 | Process tree from npm install reaching shell |
| H13 | npm install reading secrets (`.npmrc`, `.env`, `.aws/credentials`) |
| H14 | Beaconing from node after install |
| H15 | Typosquat detection via `npm_typosquats` dataset (join form) |
| H16 | Dependency confusion via private name on public registry |
| H17 | Lockfile mutation that's not user-driven |
| H18 | Cross-machine, near-simultaneous installs of the same package (worm) |

See `HUNT_MAPPING.md` for the scenario-tag ↔ hunt-ID cross-reference.
