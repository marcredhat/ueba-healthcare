#!/usr/bin/env python3
"""Exercise different lookup-table reference syntaxes for hunt H15
to find the one this tenant accepts."""
from __future__ import annotations
import os
import sys
from pathlib import Path

import requests
import urllib3
urllib3.disable_warnings()

HERE = Path(__file__).resolve().parent
SDL = Path(os.environ.get("SDL_API_DIR", str(HERE.parent.parent / "sentinelone-sdl-api")))
sys.path.insert(0, str(SDL / "scripts"))
import sdl_client  # noqa: E402
sdl_client.CONFIG_PATH = SDL / "config.json"
from sdl_client import SDLClient  # noqa: E402

c = SDLClient()
URL = f"{c.base_url}/api/powerQuery"
H = c._build_headers("log_read")


def run(label: str, q: str) -> None:
    r = requests.post(URL, headers=H,
        json={"query": q, "startTime": "24h", "priority": "low"},
        timeout=120, verify=c.verify_tls)
    print(f"=== {label} ===")
    if not r.ok:
        print(f"  HTTP{r.status_code} {r.text[:280]}\n")
        return
    j = r.json()
    cols = [x["name"] for x in (j.get("columns") or [])]
    rows = j.get("values") or []
    print(f"  cols={cols} rows={len(rows)}")
    for row in rows[:6]:
        print(f"    {row}")
    print()


# A: bare lookup name (per commands-reference.md §8)
run("A: bare-name lookup, pkg=suspect_name",
    """serverHost='developer-workstation'
| filter process.command_line matches ".*npm.*install.*"
| parse "install $pkg{regex=[a-z0-9@/_.-]+}$" from process.command_line
| filter pkg = *
| lookup known_target from npm_typosquats by pkg = suspect_name
| filter known_target = *
| group hosts=estimate_distinct(endpoint.name), first_seen=min(timestamp)
    by pkg, known_target
| sort -first_seen""")

# B: bare lookup, opposite direction
run("B: bare-name lookup, suspect_name=pkg",
    """serverHost='developer-workstation'
| filter process.command_line matches ".*npm.*install.*"
| parse "install $pkg{regex=[a-z0-9@/_.-]+}$" from process.command_line
| filter pkg = *
| lookup known_target from npm_typosquats by suspect_name = pkg
| group hosts=estimate_distinct(endpoint.name) by pkg, known_target
| sort -hosts""")

# C: lookup with just the join field (no rename)
run("C: lookup with simple key",
    """serverHost='developer-workstation'
| filter process.command_line matches ".*npm.*install.*"
| parse "install $suspect_name{regex=[a-z0-9@/_.-]+}$" from process.command_line
| filter suspect_name = *
| lookup known_target from npm_typosquats by suspect_name
| filter known_target = *
| group hosts=estimate_distinct(endpoint.name) by suspect_name, known_target""")

# D: dataset-based join (alternate pattern)
run("D: dataset + join",
    """serverHost='developer-workstation'
| filter process.command_line matches ".*npm.*install.*"
| parse "install $pkg{regex=[a-z0-9@/_.-]+}$" from process.command_line
| filter pkg = *
| join (| dataset 'config://datatables/npm_typosquats') on pkg = suspect_name
| group hosts=estimate_distinct(endpoint.name) by pkg, known_target
| sort -hosts""")
