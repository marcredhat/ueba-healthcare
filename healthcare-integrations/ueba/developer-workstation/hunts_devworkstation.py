#!/usr/bin/env python3
"""
Canonical PowerQuery library for the 18 software-supply-chain hunts
(H1..H18) — browser extensions, IDE extensions, malicious npm packages.

These are the production-reference versions, written against the standard
OCSF/SentinelOne EDR field schema:
  endpoint.name, actor.user.name,
  process.image_name, process.image_path, process.command_line,
  process.parent.image_name, process.parent.command_line, process.parent.start_time,
  process.parent.parent.image_name,
  file.path, file.content, dns.query,
  registry.key_path, registry.value
plus standard event_type / timestamp columns.

NOTE about this tenant's synthetic dataset:
  The synthetic `developer-workstation` events ingest as JSON blobs and our
  current parser extracts flat snake_case columns (endpoint_name, process_image_name,
  file_path, dns_query, etc.) — see developer-workstation/parsers/developer-workstation.conf.
  Several of these canonical queries will therefore not return rows against the
  synthetic data without either (a) re-parsing to flatten nested objects with
  dot-notation or (b) rewriting field references to the flat names.
  These queries are kept as the authoritative versions for the real EDR case
  and as the spec our parser should ultimately match.

Run:
    python3 hunts_devworkstation.py              # run all hunts
    python3 hunts_devworkstation.py --hunt H7    # run one hunt
    python3 hunts_devworkstation.py --start 48h  # widen window
    python3 hunts_devworkstation.py --print-only # show queries, don't execute
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

import requests
import urllib3
urllib3.disable_warnings()

HERE = Path(__file__).resolve().parent
SDL_API_DIR = Path(os.environ.get("SDL_API_DIR",
                                  str(HERE.parent.parent / "sentinelone-sdl-api")))
sys.path.insert(0, str(SDL_API_DIR / "scripts"))
import sdl_client  # noqa: E402
sdl_client.CONFIG_PATH = SDL_API_DIR / "config.json"
from sdl_client import SDLClient  # noqa: E402


HUNTS: list[dict] = [
    {
        "id": "H1",
        "title": "New browser extension installed in last 24h",
        "q": r"""| filter event_type in ("FILE_CREATE", "FILE_WRITE")
| filter file.path matches ".*/Extensions/[a-p]{32}/.*/manifest\\.json$"
| parse "/Extensions/$ext_id$/" from file.path
| filter ext_id = *
| group
    n = count(),
    first_seen = min(timestamp),
    users = estimate_distinct(actor.user.name),
    hosts = estimate_distinct(endpoint.name),
    sample_path = newest(file.path)
  by ext_id, endpoint.name
| sort -first_seen
| limit 100""",
    },
    {
        "id": "H2",
        "title": "Extensions requesting dangerous permissions",
        # NOTE: file.content is stored with JSON-escaped quotes (\") in this
        # tenant, so a regex looking for "\"<all_urls>\"" never matches.
        # Match on the bare permission keywords instead, which are NOT escaped.
        "q": r"""| filter file.path matches ".*/Extensions/[a-p]{32}/.*/manifest\\.json$"
| filter file.content matches ".*(<all_urls>|webRequestBlocking|cookies|declarativeNetRequest|scripting).*"
| parse "/Extensions/$ext_id$/" from file.path
| group
    n = count(),
    hosts = estimate_distinct(endpoint.name),
    users = estimate_distinct(actor.user.name)
  by ext_id
| sort -n""",
    },
    {
        "id": "H3",
        "title": "Sideloaded (non-Web Store) extensions",
        "q": r"""| filter event_type = "FILE_CREATE"
| filter file.path matches ".*/Extensions/[a-p]{32}/.*"
| filter !(process.image_name in ("chrome.exe", "msedge.exe", "brave.exe", "firefox.exe", "Google Chrome", "Microsoft Edge"))
| let ext_id = replace(file.path, "^.*?/Extensions/([a-p]{32})/.*$", "$1")
| group n = count() by ext_id, endpoint.name""",
    },
    {
        "id": "H4",
        "title": "Native messaging host abuse — registry registration",
        "q": r"""| filter event_type = "REGISTRY_SET"
| filter registry.key_path matches ".*NativeMessagingHosts.*"
| columns timestamp, endpoint.name, actor.user.name,
         process.image_name, registry.key_path, registry.value
| sort -timestamp""",
    },
    {
        "id": "H4b",
        "title": "Native messaging host abuse — rare browser children",
        "q": r"""| filter process.parent.image_name in ("chrome.exe", "msedge.exe", "brave.exe")
| filter NOT (process.image_name in ("chrome.exe", "msedge.exe", "chrome_proxy.exe", "msedgewebview2.exe"))
| group n = count(),
       hosts = estimate_distinct(endpoint.name),
       cmds  = estimate_distinct(process.command_line)
   by process.image_name, process.image_path
| filter n < 5
| sort -n""",
    },
    {
        "id": "H5",
        "title": "Browser extension beaconing — file-create variant (correlate w/ DNS)",
        "q": r"""| filter event_type = "FILE_CREATE"
| filter file.path matches ".*/Extensions/[a-p]{32}/.*"
| filter !(process.image_name in ("chrome.exe", "msedge.exe", "brave.exe", "firefox.exe", "Google Chrome", "Microsoft Edge"))
| let ext_id = replace(file.path, "^.*?/Extensions/([a-p]{32})/.*$", "$1")
| group n = count() by ext_id, endpoint.name""",
    },
    {
        "id": "H6",
        "title": "New IDE extension installation",
        "q": r"""| filter event_type in ("FILE_CREATE", "FILE_WRITE")
| filter (
    file.path matches ".*/(\\.vscode|\\.cursor|\\.windsurf)/extensions/[^/]+/package\\.json$" OR
    file.path matches ".*JetBrains/[^/]+/plugins/[^/]+/META-INF/plugin\\.xml$"
  )
| let ext_dir =
    file.path matches ".*/(\\.vscode|\\.cursor|\\.windsurf)/extensions/[^/]+/package\\.json$" ?
      replace(file.path, "^.*?/(?:\\.vscode|\\.cursor|\\.windsurf)/extensions/([^/]+)/package\\.json$", "$1") :
      replace(file.path, "^.*?JetBrains/[^/]+/plugins/([^/]+)/META-INF/plugin\\.xml$", "$1")
| filter ext_dir = *
| group
    first_seen = min(timestamp),
    hosts = estimate_distinct(endpoint.name),
    users = estimate_distinct(actor.user.name),
    sample_path = oldest(file.path)
  by ext_dir
| filter first_seen >= now() - 86400000000000
| sort -first_seen
| limit 100""",
    },
    {
        "id": "H7",
        "title": "IDE extensions executing shell commands",
        "q": r"""| filter process.parent.image_name in ("Code.exe", "code", "Code - Insiders.exe",
                                       "cursor", "Cursor.exe",
                                       "windsurf", "Windsurf.exe",
                                       "idea64.exe", "pycharm64.exe")
| filter process.image_name in ("powershell.exe", "pwsh.exe", "cmd.exe",
                                "bash", "sh", "zsh", "python", "python3",
                                "node", "curl", "wget", "certutil.exe",
                                "bitsadmin.exe", "mshta.exe", "regsvr32.exe")
| group
    n = count(),
    hosts = estimate_distinct(endpoint.name),
    sample_cmd = any(process.command_line)
  by process.image_name, process.parent.image_name
| sort -n
| limit 50""",
    },
    {
        "id": "H8",
        "title": "Workspace-trust auto-run of tasks",
        # NOTE: dropped `(timestamp - process.parent.start_time) < 30s` because
        # process.parent.start_time is not emitted by the OCSF dataset on this
        # tenant. The (IDE parent) + (--folder-uri parse) + (shell child) trio
        # is itself the correlation signal.
        # Also broadened IDE image_name list to cover the Windows/macOS spelling
        # variants observed in the synthetic data (Code.exe, Cursor.exe, ...).
        "q": r"""| filter process.parent.image_name in ("Code.exe", "Code", "code",
                                       "Cursor.exe", "Cursor", "cursor",
                                       "Windsurf.exe", "Windsurf", "windsurf")
| parse "--folder-uri[= ]+$folder{regex=[^ ]+}$" from process.parent.command_line
| filter folder = *
| filter process.image_name in ("powershell.exe", "pwsh.exe", "cmd.exe", "bash", "sh", "zsh")
| columns timestamp, endpoint.name, actor.user.name,
         folder, process.command_line, process.parent.command_line
| sort -timestamp""",
    },
    {
        "id": "H9",
        "title": "IDE accessing credential stores",
        "q": r"""| filter event_type = "FILE_READ"
| filter file.path matches ".*/\\.ssh/(id_rsa|id_ed25519|id_ecdsa|config|known_hosts)$"
  OR    file.path matches ".*/\\.aws/(credentials|config)$"
  OR    file.path matches ".*/\\.gcp/.*"
  OR    file.path matches ".*/\\.azure/.*"
  OR    file.path matches ".*/\\.netrc$"
  OR    file.path matches ".*/\\.npmrc$"
  OR    file.path matches ".*/\\.pypirc$"
  OR    file.path matches ".*/\\.docker/config\\.json$"
  OR    file.path matches ".*/\\.kube/config$"
  OR    file.path matches ".*/\\.gitconfig$"
  OR    file.path matches ".*\\.env(\\.local|\\.production|\\.development)?$"
| filter process.image_name in ("Code.exe", "code", "cursor", "windsurf",
                               "idea64.exe", "pycharm64.exe", "node", "node.exe")
  OR    process.parent.image_name in ("Code.exe", "code", "cursor", "windsurf")
| group n = count(),
       hosts = estimate_distinct(endpoint.name),
       users = estimate_distinct(actor.user.name),
       files = estimate_distinct(file.path)
   by process.image_name, process.parent.image_name
| sort -files""",
    },
    {
        "id": "H10",
        "title": "Outbound from IDE processes to non-IDE infrastructure",
        "q": r"""| filter process.image_name in ("Code.exe", "code", "cursor", "windsurf",
                                "idea64.exe", "node", "node.exe")
| filter dns.query = *
| filter !(dns.query matches ".*\\.(visualstudio\\.com|microsoft\\.com|github\\.com|githubcopilot\\.com|githubusercontent\\.com|trafficmanager\\.net|cursor\\.sh|codeium\\.com|jetbrains\\.com|gradle\\.org|maven\\.org|pypi\\.org|npmjs\\.org|nodejs\\.org)$")
| filter !(dns.query matches ".*\\.(amazonaws\\.com|azurewebsites\\.net|cloudflare\\.com)$")
| group
    n = count(),
    hosts = estimate_distinct(endpoint.name),
    first_seen = min(timestamp)
  by dns.query, process.image_name
| filter n >= 5
| sort -first_seen
| limit 100""",
    },
    {
        "id": "H11",
        "title": "Any npm install in the last 24h, with package list",
        "q": r"""| filter process.image_name in ("npm", "npm.exe", "yarn", "yarn.exe",
                                "pnpm", "pnpm.exe", "npx", "npx.exe",
                                "node", "node.exe")
| filter process.command_line matches ".*(^|\\s)(install|i|add|ci)(\\s|$).*"
| parse "(^|\\s)(install|i|add|ci) $pkgs{regex=[^-][^\\s]+(?:\\s+[^-][^\\s]+)*}$" from process.command_line
| filter pkgs = *
| group installs = count(),
        hosts = estimate_distinct(endpoint.name),
        users = estimate_distinct(actor.user.name),
        first_seen = min(timestamp)
    by pkgs, process.image_name
| sort -first_seen
| limit 200""",
    },
    {
        "id": "H12",
        "title": "Postinstall script red flags",
        "q": r"""| filter process.parent.image_name in ("npm", "yarn", "pnpm", "node",
                                       "npm.exe", "yarn.exe", "pnpm.exe", "node.exe")
| filter process.image_name in ("curl", "wget", "powershell.exe", "pwsh.exe",
                                "cmd.exe", "bash", "sh", "python", "python3",
                                "certutil.exe", "bitsadmin.exe", "iex", "base64")
| filter (
    process.command_line matches ".*(http://|https://).*" OR
    process.command_line matches ".*-enc.*" OR
    process.command_line matches ".*base64.*" OR
    process.command_line matches ".*\\$\\{.*\\}.*"
  )
| group
    n = count(),
    hosts = estimate_distinct(endpoint.name),
    first_seen = min(timestamp)
  by process.image_name, process.parent.image_name
| sort -first_seen""",
    },
    {
        "id": "H13",
        "title": "npm install reading secrets",
        "q": r"""| filter event_type = "FILE_READ"
| filter file.path matches ".*/(\\.ssh|\\.aws|\\.gcp|\\.azure|\\.npmrc|\\.pypirc|\\.dockercfg|\\.docker/config\\.json|\\.kube/config|\\.gitconfig|\\.netrc|\\.env(\\.[a-z]+)?)$"
  OR    file.path matches ".*/\\.ssh/id_(rsa|ed25519|ecdsa).*"
| filter process.image_name in ("node", "node.exe", "python", "python3")
| filter process.parent.image_name in ("npm", "yarn", "pnpm", "npx",
                                      "npm.exe", "yarn.exe", "pnpm.exe")
| group reads = count(),
       files = estimate_distinct(file.path),
       hosts = estimate_distinct(endpoint.name)
   by process.parent.command_line
| sort -files""",
    },
    {
        "id": "H14",
        "title": "Beaconing from node after install",
        # NOTE: must gate on event_type='DNS_QUERY' on this tenant — otherwise
        # rows where dns.query is null pass `= *` and pollute the output. Also
        # broadened the parent list: the synthetic data spawns malicious node
        # under IDEs (Code.exe / Cursor.exe / Windsurf.exe) as well as npm.cmd,
        # not just npm/yarn/pnpm/npx.
        "q": r"""| filter event_type = "DNS_QUERY"
| filter process.image_name in ("node", "node.exe")
| filter (
    process.parent.image_name in ("npm", "yarn", "pnpm", "npx",
                                  "npm.exe", "yarn.exe", "pnpm.exe", "npx.exe",
                                  "npm.cmd", "yarn.cmd", "pnpm.cmd",
                                  "Code.exe", "Code", "code",
                                  "Cursor.exe", "Cursor", "cursor",
                                  "Windsurf.exe", "Windsurf", "windsurf") OR
    (
      process.parent.image_name in ("node", "node.exe") AND
      process.parent.parent.image_name in ("npm", "yarn", "pnpm", "npx",
                                           "npm.exe", "yarn.exe", "pnpm.exe", "npx.exe")
    )
  )
| filter dns.query matches ".+"
| filter !(dns.query matches ".*\\.(npmjs\\.org|npmjs\\.com|yarnpkg\\.com|jsdelivr\\.net|unpkg\\.com|nodejs\\.org|github\\.com|githubusercontent\\.com)$")
| group
    n = count(),
    hosts = estimate_distinct(endpoint.name),
    first_seen = min(timestamp)
  by dns.query
| sort -first_seen
| limit 100""",
    },
    {
        "id": "H15",
        "title": "Typosquat detection via npm_typosquats dataset (join form, UI-verified)",
        "raw": True,  # don't prepend serverHost — `join` must be the first command
        "q": r"""| join
    installs = (
      serverHost='developer-workstation'
      | filter process.command_line matches ".*(^|\\s)npm\\s+i(nstall)?\\s+.*"
      | parse "(^|\\s)npm\\s+i(?:nstall)?\\s+$pkg{regex=[a-z0-9@/_.-]+}$" from process.command_line
      | filter pkg = *
      | columns pkg, endpoint.name, timestamp
    ),
    typos = (
      | dataset 'config://datatables/npm_typosquats'
      | columns suspect_name, known_target
    )
  on pkg = suspect_name
| group
    hosts = estimate_distinct(endpoint.name),
    first_seen = min(timestamp)
  by pkg, known_target
| sort -first_seen""",
    },
    {
        "id": "H16",
        "title": "Dependency confusion via private name on public registry",
        # NOTE: dependency-confusion detection rewritten.
        # Original tried to AND a process.command_line filter and dns.query on
        # the *same row*, which is impossible (process and dns are separate
        # events). It also required `--registry=` which an attacker would
        # NEVER set. Inverted logic: flag any install of an internal-scope
        # package that DOESN'T point at a private registry — the default
        # resolves to public registry.npmjs.org -> dep confusion.
        "q": r"""| filter process.image_name in ("npm", "npm.exe", "npm.cmd",
                                "yarn", "yarn.exe", "yarn.cmd",
                                "pnpm", "pnpm.exe", "pnpm.cmd")
| filter process.command_line matches ".*(^|\\s)(install|i|add)\\s+.*@(your-org|your-org-name|internal|company|corp)/.*"
| filter !(process.command_line matches ".*--registry=https?://.*")
| group
    n          = count(),
    hosts      = estimate_distinct(endpoint.name),
    users      = estimate_distinct(actor.user.name),
    first_seen = min(timestamp)
  by process.command_line
| sort -first_seen""",
    },
    {
        "id": "H17",
        "title": "Lockfile mutation that's not user-driven",
        "q": r"""| left join
    writes = (
      | filter event_type = "FILE_WRITE"
      | filter file.path matches ".*/(package-lock\\.json|yarn\\.lock|pnpm-lock\\.yaml)$"
      | columns ts = timestamp,
                endpoint = endpoint.name,
                user = actor.user.name,
                file.path,
                process.image_name,
                process.command_line
    ),
    installs = (
      | filter process.image_name in ("npm", "yarn", "pnpm", "npx",
                                      "npm.exe", "yarn.exe", "pnpm.exe", "npx.exe")
      | group last_install = max(timestamp) by endpoint = endpoint.name
    )
  on endpoint
| filter !(last_install = *) OR (ts - last_install) > 60000000000
| columns ts, endpoint, user, file.path, process.image_name, process.command_line, last_install
| sort -ts""",
    },
    {
        "id": "H18",
        "title": "Cross-machine, near-simultaneous installs of the same package (worm)",
        # NOTE: image_name list broadened to include the .exe and .cmd
        # variants the synthetic data actually emits — without these,
        # 99% of npm install events are excluded.
        "q": r"""| filter process.image_name in ("npm", "npm.exe", "npm.cmd",
                                "yarn", "yarn.exe", "yarn.cmd",
                                "pnpm", "pnpm.exe", "pnpm.cmd",
                                "npx", "npx.exe")
| filter process.command_line matches ".*(^|\\s)install(\\s|$).*"
| parse "install $pkg{regex=[a-z0-9@/_.-]+}$" from process.command_line
| filter pkg = *
| group
    hosts = estimate_distinct(endpoint.name),
    users = estimate_distinct(actor.user.name),
    first_seen = min(timestamp),
    last_seen = max(timestamp)
  by pkg, bucket_30m = timebucket('30 minutes')
| filter hosts >= 5
| let span_min = (last_seen - first_seen) / 60000000000
| filter span_min < 30
| sort -hosts""",
    },
]


# Scope each query to the developer-workstation dataset on this tenant.
SCOPE = "serverHost='developer-workstation'"


def run_query(c: SDLClient, q: str, start: str) -> tuple[int, dict | None, str]:
    try:
        r = requests.post(
            f"{c.base_url}/api/powerQuery",
            headers=c._build_headers("log_read"),
            json={"query": q + "\n| limit 50", "startTime": start, "priority": "low"},
            timeout=180, verify=c.verify_tls,
        )
    except Exception as e:
        return 0, None, str(e)[:200]
    if not r.ok:
        return r.status_code, None, r.text[:300]
    try:
        return r.status_code, r.json(), ""
    except Exception:
        return r.status_code, None, "non-json"


def fmt_table(j: dict, max_rows: int = 5) -> str:
    cols = [c["name"] for c in (j.get("columns") or [])]
    rows = (j.get("values") or [])[:max_rows]
    if not cols:
        return "    (no columns)"
    widths = [max(len(str(c)), 8) for c in cols]
    for row in rows:
        widths = [max(w, len(str(v))) for w, v in zip(widths, row)]
    widths = [min(w, 50) for w in widths]
    fmt = "    " + "  ".join("{:<" + str(w) + "}" for w in widths)
    out = [fmt.format(*cols), fmt.format(*["-" * w for w in widths])]
    for row in rows:
        out.append(fmt.format(*[str(v)[:50] for v in row]))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hunt", default=None, help="run only this hunt id (e.g. H7)")
    ap.add_argument("--start", default="24h", help="startTime window")
    ap.add_argument("--show-rows", type=int, default=3, help="rows to dump per pass")
    ap.add_argument("--print-only", action="store_true",
                    help="print the queries, do not execute")
    args = ap.parse_args()

    targets = [h for h in HUNTS if not args.hunt or h["id"] == args.hunt]
    if not targets:
        print(f"No hunt matches '{args.hunt}'"); return 2

    if args.print_only:
        for h in targets:
            print("=" * 78)
            print(f"{h['id']}  {h['title']}")
            print("=" * 78)
            print(SCOPE)
            print(h["q"])
            print()
        return 0

    c = SDLClient()
    print(f"Tenant : {c.base_url}")
    print(f"Scope  : {SCOPE}")
    print(f"Start  : {args.start}\n")

    passed = failed = errored = 0
    results: list[tuple[str, str, int, int]] = []
    for h in targets:
        q = h["q"] if h.get("raw") else f"{SCOPE}\n{h['q']}"
        code, j, err = run_query(c, q, args.start)
        if j is None:
            print(f"[ERROR HTTP{code}] {h['id']:<4} {h['title']}")
            print(f"  {err[:280]}")
            errored += 1
            results.append((h["id"], "ERROR", 0, code))
            continue
        rows = len(j.get("values") or [])
        if rows > 0:
            passed += 1
            print(f"[PASS rows={rows:>3}] {h['id']:<4} {h['title']}")
            if args.show_rows > 0:
                print(fmt_table(j, args.show_rows))
            results.append((h["id"], "PASS", rows, code))
        else:
            failed += 1
            print(f"[FAIL rows=  0] {h['id']:<4} {h['title']}")
            results.append((h["id"], "FAIL", 0, code))

    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed}/{len(targets)} pass, {failed} fail (0 rows), {errored} error")
    for hid, status, n, code in results:
        marker = {"PASS": "OK", "FAIL": "--", "ERROR": "!!"}[status]
        print(f"  {marker} {hid:<4} {status:<5} rows={n:<4} http={code}")
    return 0 if (failed == 0 and errored == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
