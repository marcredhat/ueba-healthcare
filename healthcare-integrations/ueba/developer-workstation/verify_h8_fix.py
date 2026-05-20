#!/usr/bin/env python3
"""Verify H8 fix: drop the broken start_time-window filter.
`process.parent.start_time` is not emitted by the generator, so the
`(timestamp - process.parent.start_time) < 30s` predicate evaluates to
NULL and removes every row. The IDE-parent + --folder-uri parse + shell-
child combination is itself the correlation signal.
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

SDL = Path(os.environ.get("SDL_API_DIR",
    _default_sdl_dir()))
cfg = json.load(open(SDL / "config.json"))
H = {"Authorization": f"Bearer {cfg['console_api_token']}",
     "Content-Type":  "application/json"}
B = cfg["base_url"].rstrip("/")

QUERY = r"""serverHost='developer-workstation'
| filter process.parent.image_name in ("Code.exe", "Code", "code", "Cursor.exe", "Cursor", "cursor",
                                       "Windsurf.exe", "Windsurf", "windsurf")
| parse "--folder-uri[= ]+$folder{regex=[^ ]+}$" from process.parent.command_line
| filter folder = *
| filter process.image_name in ("powershell.exe", "pwsh.exe", "cmd.exe", "bash", "sh", "zsh")
| columns timestamp, endpoint.name, actor.user.name,
          folder, process.command_line, process.parent.command_line
| sort -timestamp
| limit 25
"""
print("Query:")
for line in QUERY.splitlines(): print(f"  {line}")
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
for i, row in enumerate(rows[:10]):
    print(f"--- {i+1} ---")
    for c, v in zip(cols, row):
        s = str(v)
        print(f"  {c:30}  {s[:140]}")
