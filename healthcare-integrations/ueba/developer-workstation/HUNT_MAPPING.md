# Developer-workstation synthetic events → hunt mapping

Each scenario in `sample-data/generate_devworkstation_events.py` emits a chain
of events tagged with one or more `_hunt_id` values. Use this table to verify
that a hunt query produces results when run against the generated data.

## Coverage matrix

| Hunt | Description | Scenarios that fire it | Event types involved |
|---|---|---|---|
| **H1** | New browser extension install (24h) | `legit_browser_extension_install`, `dangerous_perms_extension`, `sideloaded_chrome_extension` | `FILE_CREATE` on `*/Extensions/[a-p]{32}/.../manifest.json` |
| **H2** | Extension with dangerous permission combo | `dangerous_perms_extension` | `FILE_CREATE` with manifest content containing `<all_urls>` + `cookies` + `webRequest` |
| **H3** | Sideloaded extension (non-browser writer) | `sideloaded_chrome_extension` | `FILE_CREATE` by dropper process (e.g. `svc_helper.exe`, `powershell.exe` child) |
| **H4** | Native messaging host registration / launch | `native_messaging_host_registered`, `native_messaging_host_launch` | `REGISTRY_SET` on `HKCU\...\NativeMessagingHosts\*`, followed by `PROCESS_START` of the host binary |
| **H5** | Browser process beaconing to C2 | `browser_extension_beacon` | `DNS_QUERY` from `chrome.exe` / `Google Chrome` to `*.workers.dev`, `*.trycloudflare.com`, etc. |
| **H6** | New IDE extension install | `legit_ide_extension_install`, `malicious_ide_extension_install` | `FILE_CREATE` on `~/.vscode/extensions/<dir>/package.json` (and Cursor/Windsurf variants) |
| **H7** | IDE spawns suspicious shell | `ide_spawns_suspicious_shell` | `PROCESS_START` of `powershell.exe -enc`, `certutil`, `curl ... | sh` parented by Code/Cursor/Windsurf |
| **H8** | Workspace-trust auto-task on folder open | `ide_spawns_suspicious_shell` (parent cmd contains `--folder-uri`) | `PROCESS_START` w/ `<30s` delta from parent IDE start |
| **H9** | IDE reads credential files | `ide_extension_reads_creds` | `FILE_READ` of `~/.ssh/*`, `~/.aws/credentials`, `~/.kube/config`, `.env`, etc., by `node` parented by IDE |
| **H10** | IDE / node beaconing to non-IDE infra | `ide_beacon` | `DNS_QUERY` to C2 domains, process parent is `Code.exe`/`Cursor.exe`/`Windsurf.exe` |
| **H11** | Inventory of npm installs | `legit_npm_install`, `malicious_npm_install_*`, `shai_hulud_worm_burst` | `PROCESS_START` of `npm`/`yarn`/`pnpm` with `install` in command line |
| **H12** | Postinstall script red flags | `postinstall_script_node`, `postinstall_curl` | `PROCESS_START` of `node` / `curl` / `powershell` parented by `npm` |
| **H13** | npm install reading secrets | `postinstall_reads_creds` | `FILE_READ` of credentials by `node` whose parent is `npm` |
| **H14** | `node` beaconing post-install | `postinstall_c2_dns` | `DNS_QUERY` from `node` (parented by `npm`) to non-registry domains |
| **H15** | Typosquat install | `malicious_npm_install_typosquat` | `PROCESS_START` of `npm install expres` / `loadash` / `colorss` / `requesst` |
| **H16** | Dependency confusion | `malicious_npm_install_dep_confusion`, `dep_confusion_registry` | `PROCESS_START` of `npm install @your-org/...` followed by `DNS_QUERY` to `registry.npmjs.org` |
| **H17** | Lockfile mutation without preceding install | `lockfile_mutation_no_install` | `FILE_WRITE` to `package-lock.json` by a non-package-manager process (`wscript.exe`, `osascript`) |
| **H18** | Cross-host install burst (worm) | `shai_hulud_worm_burst` | Multiple `PROCESS_START` events of the same `npm install <pkg>` on 5+ hosts within 10 minutes |

## Endpoint population

The generator models a fleet of ~50 dev workstations distributed across Berlin,
Hamburg, Munich, Frankfurt, London, NYC, with a mix of Windows 11, macOS 15,
and Ubuntu 24.04. Twenty-five named developer accounts produce activity.

## Volume tuning

`generate_events(count, hours_back, seed)` aims for approximately `count`
*target* events; the actual NDJSON line count will be larger because each
malicious scenario emits a chain (e.g. `postinstall_malware` produces
~6 correlated events: process, postinstall, file reads, curl child, DNS).

A `count=800` run typically emits 800–1200 lines and covers all 18 hunts.

## Pipeline integration

The generator is wired into `raw-logs/generate_rotated_logs.py`. Running
that script produces hourly-rotated `.ndjson.gz` files under
`raw-logs/developer-workstation/YYYY/MM/DD/`. Verified 18/18 hunt coverage
across the hourly bundles.

## Field schema for hunt queries

PowerQueries written against this data should pivot on:

| Top-level field | Sub-fields used |
|---|---|
| `event_type` | `FILE_CREATE`, `FILE_READ`, `FILE_WRITE`, `PROCESS_START`, `DNS_QUERY`, `REGISTRY_SET` |
| `endpoint` | `endpoint.name`, `endpoint.os` |
| `actor` | `actor.user.name` |
| `process` | `process.image_name`, `process.image_path`, `process.command_line`, `process.pid`, `process.parent.image_name`, `process.parent.command_line` |
| `file` | `file.path`, `file.action`, `file.content_sample` |
| `dns` | `dns.query`, `dns.response_ip` |
| `registry` | `registry.key_path`, `registry.value_name`, `registry.value` |
| `_hunt_id` | list of hunt IDs the event is intended to trip (test signal) |
| `_scenario` | scenario tag (test signal) |

Strip `_hunt_id` and `_scenario` before deploying to production tenants —
they exist to make the synthetic stream self-labelling for hunt verification.

## Adding new hunts

1. Add a `scenario_*` function in `generate_devworkstation_events.py`.
2. Tag emitted events with the appropriate `_hunt_id` list.
3. Add a row to `SCENARIO_MIX` with a sensible weight.
4. Add a row to the coverage matrix above.
5. Re-run `test_generator.py` to confirm the new hunt ID appears.
