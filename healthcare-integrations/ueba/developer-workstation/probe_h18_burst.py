#!/usr/bin/env python3
"""Diagnose H18: burst-install (>=5 hosts <30min) returns 0.

Probable issues:
  A. `timebucket('30 minutes')` syntax may differ on this tenant.
  B. The synthetic dataset may not have any package installed by >=5
     distinct hosts inside a 30-minute window.
  C. The `let X = (last - first) / 60000000000` cast may not work with
     timestamps that are objects, not ints, in this tenant.
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
        json={"query":q,"startTime":w,"priority":"low"},
        timeout=120, verify=False)
    print(f"\n=== {label} ===  HTTP{r.status_code}")
    if not r.ok:
        print(f"  {r.text[:300]}")
        return
    j=r.json(); cols=[c["name"] for c in (j.get("columns") or [])]; rows=j.get("values") or []
    print(f"  cols={cols}  rows={len(rows)}")
    for row in rows[:10]:
        print("  ", [str(v)[:80] for v in row])


# 1 — how many distinct hosts install each package, irrespective of time?
run("1: top packages by distinct host count (24h)",
    f"{SH} | filter process.image_name in ('npm','npm.exe','npm.cmd','yarn','pnpm','npx')"
    " | filter process.command_line matches '.*(^|\\\\s)install(\\\\s|$).*'"
    " | parse 'install $pkg{regex=[a-z0-9@/_.-]+}$' from process.command_line"
    " | filter pkg = *"
    " | group hosts = estimate_distinct(endpoint.name),"
    "         n     = count(),"
    "         first_seen = min(timestamp),"
    "         last_seen  = max(timestamp)"
    "   by pkg"
    " | sort -hosts | limit 15")

# 2 — same but bound to a 30-min sliding bucket using `timeslice`
run("2: timeslice('30m') bucketing (alt syntax to timebucket)",
    f"{SH} | filter process.image_name in ('npm','npm.exe','npm.cmd','yarn','pnpm','npx')"
    " | filter process.command_line matches '.*(^|\\\\s)install(\\\\s|$).*'"
    " | parse 'install $pkg{regex=[a-z0-9@/_.-]+}$' from process.command_line"
    " | filter pkg = *"
    " | group hosts = estimate_distinct(endpoint.name),"
    "         first = min(timestamp), last = max(timestamp)"
    "   by pkg, bucket = timeslice('30m')"
    " | sort -hosts | limit 10")

# 3 — try `timebucket` exact form
run("3: timebucket('30 minutes') as user wrote",
    f"{SH} | filter process.image_name in ('npm','npm.exe','npm.cmd','yarn','pnpm','npx')"
    " | filter process.command_line matches '.*(^|\\\\s)install(\\\\s|$).*'"
    " | parse 'install $pkg{regex=[a-z0-9@/_.-]+}$' from process.command_line"
    " | filter pkg = *"
    " | group hosts = estimate_distinct(endpoint.name)"
    "   by pkg, bucket_30m = timebucket('30 minutes')"
    " | sort -hosts | limit 10")
