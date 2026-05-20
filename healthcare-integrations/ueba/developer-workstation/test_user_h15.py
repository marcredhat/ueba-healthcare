#!/usr/bin/env python3
"""Reproduce the user's exact H15 query and try multiple lookup-table
path conventions to find which one this tenant actually accepts."""
from __future__ import annotations
import os, sys
from pathlib import Path

import requests, urllib3
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
    print(f"=== {label} ===")
    r = requests.post(URL, headers=H,
        json={"query": q, "startTime": "24h", "priority": "low"},
        timeout=120, verify=c.verify_tls)
    if not r.ok:
        print(f"  HTTP{r.status_code} {r.text[:240]}\n")
        return
    j = r.json()
    cols = [x["name"] for x in (j.get("columns") or [])]
    rows = j.get("values") or []
    print(f"  cols={cols} rows={len(rows)}")
    for row in rows[:5]:
        print(f"    {row}")
    print()


SCOPE = "serverHost='developer-workstation'"

# 1) User's exact pasted query, bare name
run("user verbatim — bare 'npm_typosquats'", f"""{SCOPE}
| filter process.command_line matches ".*(^|\\\\s)npm\\\\s+i(nstall)?\\\\s+.*"
| parse "(^|\\\\s)npm\\\\s+i(?:nstall)?\\\\s+$pkg{{regex=[a-z0-9@/_.-]+}}$" from process.command_line
| filter pkg = *
| lookup known_target from npm_typosquats by suspect_name = pkg
| filter known_target = *
| group
    hosts = estimate_distinct(endpoint.name),
    first_seen = min(timestamp)
  by pkg, known_target
| sort -first_seen""")

# 2) Same, but lookup name in quotes
run("user verbatim — quoted 'npm_typosquats'", f"""{SCOPE}
| filter process.command_line matches ".*(^|\\\\s)npm\\\\s+i(nstall)?\\\\s+.*"
| parse "(^|\\\\s)npm\\\\s+i(?:nstall)?\\\\s+$pkg{{regex=[a-z0-9@/_.-]+}}$" from process.command_line
| filter pkg = *
| lookup known_target from 'npm_typosquats' by suspect_name = pkg
| filter known_target = *
| group hosts = estimate_distinct(endpoint.name) by pkg, known_target""")

# 3) Same, but with /datatables/ prefix
run("user verbatim — datatables/npm_typosquats", f"""{SCOPE}
| filter process.command_line matches ".*(^|\\\\s)npm\\\\s+i(nstall)?\\\\s+.*"
| parse "(^|\\\\s)npm\\\\s+i(?:nstall)?\\\\s+$pkg{{regex=[a-z0-9@/_.-]+}}$" from process.command_line
| filter pkg = *
| lookup known_target from datatables/npm_typosquats by suspect_name = pkg
| filter known_target = *
| group hosts = estimate_distinct(endpoint.name) by pkg, known_target""")

# 4) Drop the complex parse — use the SAME simple parse that PROVED to work
run("simple parse + bare lookup (our working form)", f"""{SCOPE}
| filter process.image_name in ("npm", "npm.exe", "npm.cmd", "yarn", "pnpm", "npx")
| filter process.command_line matches ".*(install|i|add).*"
| parse "(install|i|add) $pkg{{regex=[a-z0-9@/_.-]+}}$" from process.command_line
| filter pkg = *
| lookup known_target from npm_typosquats by suspect_name = pkg
| filter known_target = *
| group hosts = estimate_distinct(endpoint.name) by pkg, known_target
| sort -hosts""")
