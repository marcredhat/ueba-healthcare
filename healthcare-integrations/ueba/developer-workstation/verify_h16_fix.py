#!/usr/bin/env python3
"""Verify the corrected H16: dependency-confusion detection.

Logic: any internal-scope install (e.g. `@your-org/secret-lib`) on a dev
workstation that doesn't explicitly override `--registry=` will resolve
to the public registry.npmjs.org -> dependency confusion risk.
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

QUERY = r"""serverHost='developer-workstation'
| filter process.image_name in ("npm", "npm.exe", "npm.cmd",
                                "yarn", "yarn.exe", "yarn.cmd",
                                "pnpm", "pnpm.exe", "pnpm.cmd")
| filter process.command_line matches ".*(^|\\s)(install|i|add)\\s+.*@(your-org|your-org-name|internal|company|corp)/.*"
| filter !(process.command_line matches ".*--registry=https?://.*")
| group
    n           = count(),
    hosts       = estimate_distinct(endpoint.name),
    users       = estimate_distinct(actor.user.name),
    first_seen  = min(timestamp)
  by process.command_line
| sort -first_seen
"""
print("Query:")
for ln in QUERY.splitlines(): print(f"  {ln}")
print()

r = requests.post(f"{B}/api/powerQuery", headers=H,
    json={"query": QUERY, "startTime": "24h", "priority": "low"},
    timeout=90, verify=False)
print(f"HTTP{r.status_code}")
if not r.ok: raise SystemExit(r.text[:400])
j = r.json()
cols = [c["name"] for c in (j.get("columns") or [])]
rows = j.get("values") or []
print(f"cols: {cols}")
print(f"rows: {len(rows)}\n")
for row in rows[:20]:
    print(" ", row)
