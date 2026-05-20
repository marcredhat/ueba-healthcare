#!/usr/bin/env python3
"""Verify the H2 fix: file.content stores JSON-escaped quotes
(``\\"<all_urls>\\"``), so the original tuple/regex matches looking for
``"<all_urls>"`` find nothing. Dropping the quotes from the regex makes
the keyword match work.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

import requests
import urllib3

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

QUERY = (
    "serverHost='developer-workstation'\n"
    "| filter file.path matches '.*/Extensions/[a-p]{32}/.*/manifest\\\\.json$'\n"
    "| filter file.content matches '.*(<all_urls>|webRequestBlocking|cookies"
        "|declarativeNetRequest|scripting).*'\n"
    "| parse '/Extensions/$ext_id$/' from file.path\n"
    "| group\n"
    "    n     = count(),\n"
    "    hosts = estimate_distinct(endpoint.name),\n"
    "    users = estimate_distinct(actor.user.name)\n"
    "  by ext_id\n"
    "| sort -n"
)

print("Query:")
for line in QUERY.splitlines():
    print(f"  {line}")
print()

r = requests.post(f"{B}/api/powerQuery", headers=H,
    json={"query": QUERY, "startTime": "24h", "priority": "low"},
    timeout=90, verify=False)
print(f"HTTP{r.status_code}")
if not r.ok:
    print(r.text[:400])
    raise SystemExit(1)

j = r.json()
cols = [c["name"] for c in (j.get("columns") or [])]
rows = j.get("values") or []
print(f"cols: {cols}")
print(f"rows: {len(rows)}\n")

widths = [max(len(c), 12) for c in cols]
print("  " + "  ".join(f"{c:<{w}}" for c, w in zip(cols, widths)))
print("  " + "  ".join("-" * w for w in widths))
for row in rows[:25]:
    print("  " + "  ".join(f"{str(v):<{w}}" for v, w in zip(row, widths)))
