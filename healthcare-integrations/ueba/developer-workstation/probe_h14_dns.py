#!/usr/bin/env python3
"""Diagnose H14: why FILE_READ events are reaching the group-by on dns.query.

Hypothesis: `filter dns.query = *` doesn't strip rows where dns.query is
null/empty on this tenant for events that simply don't have a dns block.
Fix: gate the query by event_type and/or require a non-empty regex match.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import requests, urllib3

# --- portable SDL_API_DIR resolution -----------------------------------
def _default_sdl_dir() -> str:
    """Locate ../../sentinelone-sdl-api relative to this script."""
    import pathlib as _p
    return str(_p.Path(__file__).resolve().parent.parent.parent / 'sentinelone-sdl-api')
urllib3.disable_warnings()

cfg = json.load(open(os.environ.get("SDL_API_DIR",
    _default_sdl_dir()) + "/config.json"))
H = {"Authorization": f"Bearer {cfg['console_api_token']}",
     "Content-Type":  "application/json"}
B = cfg["base_url"].rstrip("/")
SH = "serverHost='developer-workstation'"

def run(label, q, w="24h"):
    print(f"=== {label} ===")
    r = requests.post(f"{B}/api/powerQuery", headers=H,
        json={"query":q,"startTime":w,"priority":"low"},
        timeout=90, verify=False)
    print(f"  HTTP{r.status_code}")
    if not r.ok: print(f"  ERR {r.text[:300]}\n"); return
    j=r.json(); cols=[c["name"] for c in (j.get("columns") or [])]
    rows=j.get("values") or []
    print(f"  cols={cols}  rows={len(rows)}")
    for row in rows[:10]: print(f"    {row}")
    print()

# 1 — sanity: distinct event_types currently in dataset
run("1: event_type breakdown",
    f"{SH} | group n=count() by event_type | sort -n")

# 2 — does `= *` actually exclude FILE_READ rows?
run("2: FILE_READ rows that pass `filter dns.query = *`",
    f"{SH} | filter event_type = 'FILE_READ' | filter dns.query = * | columns event_type, dns.query, file.path | limit 5")

# 3 — does requiring a non-empty value strip them?
run("3: stronger filter `dns.query matches '.+'`",
    f"{SH} | filter event_type = 'FILE_READ' | filter dns.query matches '.+' | columns event_type, dns.query, file.path | limit 5")

# 4 — the corrected H14 (gate on event_type = DNS_QUERY)
run("4: corrected H14 — gate on event_type",
    f"{SH} | filter event_type = 'DNS_QUERY'"
    " | filter process.image_name in ('node','node.exe')"
    " | filter (process.parent.image_name in ('npm','yarn','pnpm','npx','npm.exe','yarn.exe','pnpm.exe','npx.exe')"
    "   OR (process.parent.image_name in ('node','node.exe')"
    "       AND process.parent.parent.image_name in ('npm','yarn','pnpm','npx','npm.exe','yarn.exe','pnpm.exe','npx.exe')))"
    " | filter dns.query matches '.+'"
    " | filter !(dns.query matches '.*\\\\.(npmjs\\\\.org|npmjs\\\\.com|yarnpkg\\\\.com|jsdelivr\\\\.net|unpkg\\\\.com|nodejs\\\\.org|github\\\\.com|githubusercontent\\\\.com)$')"
    " | group n=count(), hosts=estimate_distinct(endpoint.name), first_seen=min(timestamp) by dns.query"
    " | sort -first_seen | limit 50")
