#!/usr/bin/env python3
"""Verify the corrected H14: node-child DNS to non-allowlisted domain."""
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

QUERY = r"""serverHost='developer-workstation'
| filter event_type = "DNS_QUERY"
| filter process.image_name in ("node", "node.exe")
| filter (
    process.parent.image_name in ("npm", "yarn", "pnpm", "npx",
                                  "npm.exe", "yarn.exe", "pnpm.exe", "npx.exe",
                                  "npm.cmd", "yarn.cmd", "pnpm.cmd",
                                  "Code.exe", "Code", "code",
                                  "Cursor.exe", "Cursor", "cursor",
                                  "Windsurf.exe", "Windsurf", "windsurf")
    OR (
      process.parent.image_name in ("node", "node.exe") AND
      process.parent.parent.image_name in ("npm", "yarn", "pnpm", "npx",
                                           "npm.exe", "yarn.exe", "pnpm.exe", "npx.exe")
    )
  )
| filter dns.query matches ".+"
| filter !(dns.query matches ".*\\.(npmjs\\.org|npmjs\\.com|yarnpkg\\.com|jsdelivr\\.net|unpkg\\.com|nodejs\\.org|github\\.com|githubusercontent\\.com)$")
| group
    n          = count(),
    hosts      = estimate_distinct(endpoint.name),
    first_seen = min(timestamp)
  by dns.query
| sort -first_seen
| limit 100
"""

print("Query:")
for ln in QUERY.splitlines(): print(f"  {ln}")
print()

r = requests.post(f"{B}/api/powerQuery", headers=H,
    json={"query": QUERY, "startTime": "24h", "priority": "low"},
    timeout=120, verify=False)
print(f"HTTP{r.status_code}")
if not r.ok: raise SystemExit(r.text[:400])
j = r.json()
cols = [c["name"] for c in (j.get("columns") or [])]
rows = j.get("values") or []
print(f"cols: {cols}")
print(f"rows: {len(rows)}\n")
for row in rows[:20]:
    print(" ", row)
