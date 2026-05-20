#!/usr/bin/env python3
"""Diagnose H16 (dependency confusion): does the generator emit
'@your-org-name/* --registry=https://registry.npmjs.org' npm-install
commands? And is the broken single-event AND across process+dns the
sole reason the user's query returned 0?
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
    r = requests.post(f"{B}/api/powerQuery", headers=H,
        json={"query": q, "startTime": w, "priority": "low"},
        timeout=90, verify=False)
    print(f"\n=== {label} ===  HTTP{r.status_code}")
    if not r.ok:
        print(f"  {r.text[:300]}")
        return
    j = r.json()
    cols = [c["name"] for c in (j.get("columns") or [])]
    rows = j.get("values") or []
    print(f"  cols={cols}  rows={len(rows)}")
    for row in rows[:10]:
        print("  ", [str(v)[:120] for v in row])


run("1: any --registry= flag observed in npm/yarn cmdlines?",
    f"{SH} | filter process.image_name in ('npm','npm.exe','npm.cmd','yarn','yarn.exe')"
    " | filter process.command_line matches '.*--registry=.*'"
    " | columns endpoint.name, process.command_line | limit 10")

run("2: @your-org-name / internal scopes installed?",
    f"{SH} | filter process.command_line matches '.*@(your-org-name|internal|your-org)/.*'"
    " | columns endpoint.name, process.image_name, process.command_line | limit 10")

run("3: DNS to registry.npmjs.org",
    f"{SH} | filter event_type='DNS_QUERY' | filter dns.query = 'registry.npmjs.org'"
    " | columns endpoint.name, dns.query, process.image_name, process.parent.image_name | limit 10")

# the user's query verbatim, AND on a single row — should be 0
run("4: user's exact filter (single-event AND of process AND dns)",
    f"{SH} | filter process.image_name in ('npm','npm.exe','yarn','yarn.exe')"
    " | filter process.command_line matches '.*--registry=.*'"
    "   AND process.command_line matches '.*@(your-org-name|internal)/.*'"
    " | filter dns.query = 'registry.npmjs.org'"
    " | limit 5")
