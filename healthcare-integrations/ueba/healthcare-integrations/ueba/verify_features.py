#!/usr/bin/env python3
"""Verify ueba_features_hourly was populated after running file 01."""
import sys
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

SDL_API_DIR = Path("/Users/marc.chisinevski/windsurf/shared/sentinelone-sdl-api")
sys.path.insert(0, str(SDL_API_DIR / "scripts"))

import sdl_client  # noqa: E402

sdl_client.CONFIG_PATH = SDL_API_DIR / "config.json"
from sdl_client import SDLClient  # noqa: E402

c = SDLClient()
url = f"{c.base_url}/api/powerQuery"
H = c._build_headers("log_read")


def run(label, query, start="24h"):
    r = requests.post(
        url, headers=H,
        json={"query": query, "startTime": start, "priority": "low"},
        timeout=60, verify=c.verify_tls,
    )
    print(f"\n=== {label} ===  HTTP {r.status_code}")
    if not r.ok:
        print(r.text[:500])
        return
    d = r.json()
    cols = [c_["name"] for c_ in (d.get("columns") or [])]
    vals = d.get("values") or []
    print(f"  matchingEvents={d.get('matchingEvents')}  rows={len(vals)}")
    print(f"  columns: {cols}")
    for row in vals[:20]:
        print(f"    {row}")
    if len(vals) > 20:
        print(f"    ... +{len(vals) - 20} more")


run("row count grouped by feature_name",
    "| dataset 'config://datatables/ueba_features_hourly' "
    "| group rows = count() by feature_name "
    "| sort -rows")

run("first 10 raw rows",
    "| dataset 'config://datatables/ueba_features_hourly' | limit 10")

run("distinct entity_ids written",
    "| dataset 'config://datatables/ueba_features_hourly' "
    "| group hours = count() by entity_id "
    "| sort -hours")

run("total rows in datatable",
    "| dataset 'config://datatables/ueba_features_hourly' | group total = count()")
