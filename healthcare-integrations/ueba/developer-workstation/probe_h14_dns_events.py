#!/usr/bin/env python3
"""Inventory DNS_QUERY events in the dev-workstation dataset to fix H14.

Probes performed:
  A) event_type breakdown of the whole tenant feed
  B) raw DNS_QUERY events — does dns.query come out clean?
  C) DNS_QUERY events with node as the process — these are the ones H14
     wants to flag
  D) DNS_QUERY by (process, parent) pair so we know what the parent chain
     looks like in the real data (e.g. is the parent `npm.cmd` or `npm`?)
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
    for row in rows[:15]:
        print("  ", [str(v)[:80] for v in row])


run("A: event_type breakdown (24h)",
    f"{SH} | group n=count() by event_type | sort -n")

run("B: raw DNS_QUERY events — is dns.query clean?",
    f"{SH} | filter event_type='DNS_QUERY'"
    " | columns endpoint.name, dns.query, process.image_name, process.parent.image_name | limit 8")

run("C: DNS_QUERY events with node child",
    f"{SH} | filter event_type='DNS_QUERY'"
    " | filter process.image_name in ('node','node.exe')"
    " | columns dns.query, process.image_name, process.parent.image_name, process.parent.parent.image_name | limit 10")

run("D: DNS_QUERY (process, parent, grandparent) shape",
    f"{SH} | filter event_type='DNS_QUERY'"
    " | group n=count() by process.image_name, process.parent.image_name, process.parent.parent.image_name | sort -n")
