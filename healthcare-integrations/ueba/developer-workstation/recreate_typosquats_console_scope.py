#!/usr/bin/env python3
"""Re-create the npm_typosquats lookup table using the console_api_token
(same auth the AI SIEM UI uses) so the lookup is visible from the UI's
PowerQuery search. Also delete-then-recreate in case a stale stub at a
different scope is shadowing it.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

import requests
import urllib3
urllib3.disable_warnings()

HERE = Path(__file__).resolve().parent
SDL = Path(os.environ.get("SDL_API_DIR", str(HERE.parent.parent / "sentinelone-sdl-api")))

with open(SDL / "config.json") as f:
    cfg = json.load(f)

BASE = cfg["base_url"].rstrip("/")
CONSOLE_TOKEN = cfg.get("console_api_token") or cfg.get("config_write_key") or ""
SCOPE = cfg.get("s1_scope") or ""

if not CONSOLE_TOKEN:
    print("ERROR: no console_api_token (or config_write_key) in config.json", file=sys.stderr)
    sys.exit(2)

H = {"Authorization": f"Bearer {CONSOLE_TOKEN}", "Content-Type": "application/json"}
if SCOPE:
    H["S1-Scope"] = SCOPE
print(f"Tenant : {BASE}")
scope_label = SCOPE or "(default — token scope)"
print(f"Scope  : {scope_label}")
print()

PATH = "/datatables/npm_typosquats"

TYPOSQUATS: list[tuple[str, str]] = [
    ("expres",                   "express"),
    ("loadash",                  "lodash"),
    ("colorss",                  "colors"),
    ("requesst",                 "request"),
    ("eslint-config-airbnb-pro", "eslint-config-airbnb"),
    ("event-stream-helper",      "event-stream"),
    ("ua-parser-utils",          "ua-parser-js"),
    ("lodash-utils",             "lodash"),
    ("lodaash",                  "lodash"),
    ("expresss",                 "express"),
    ("axios-lib",                "axios"),
    ("axioss",                   "axios"),
    ("reactt",                   "react"),
    ("react-utility",            "react"),
    ("vuetify-utils",            "vuetify"),
    ("commaander",               "commander"),
    ("yargs-plus",               "yargs"),
    ("chalkk",                   "chalk"),
    ("chalk-cli",                "chalk"),
    ("nextt",                    "next"),
    ("webpackk",                 "webpack"),
    ("typescriptt",              "typescript"),
    ("debugg",                   "debug"),
    ("moment-tz",                "moment"),
    ("uuid-gen",                 "uuid"),
]

content = json.dumps({
    "columnNames": ["suspect_name", "known_target"],
    "rows":        [list(p) for p in TYPOSQUATS],
})

# --- 1. read current version (if any) for CAS guard ----------------------
print(f"[1/3] getFile {PATH}")
g = requests.post(f"{BASE}/api/getFile", headers=H,
    json={"path": PATH}, timeout=30, verify=False)
print(f"      HTTP{g.status_code}  {g.text[:160]}")
version = g.json().get("version") if g.ok else None
print(f"      existing version: {version}")

# --- 2. putFile with the console_api_token -------------------------------
print(f"\n[2/3] putFile {PATH}  ({len(TYPOSQUATS)} rows)")
body = {"path": PATH, "content": content, "prettyprint": True}
if version is not None:
    body["expectedVersion"] = version
p = requests.post(f"{BASE}/api/putFile", headers=H,
    json=body, timeout=60, verify=False)
print(f"      HTTP{p.status_code}  {p.text[:200]}")

# --- 3. read it back and confirm via the same auth -----------------------
print(f"\n[3/3] verify by reading back {PATH}")
v = requests.post(f"{BASE}/api/getFile", headers=H,
    json={"path": PATH}, timeout=30, verify=False)
print(f"      HTTP{v.status_code}")
if v.ok:
    j = v.json()
    parsed = json.loads(j.get("content", "{}"))
    rows = parsed.get("rows", [])
    print(f"      version={j.get('version')}  rows={len(rows)}")
    for r in rows[:3]:
        print(f"        {r}")
    print("      ...")

# --- 4. confirm visibility from PowerQuery via same console token --------
print(f"\n[4/4] confirm lookup visible from powerQuery (same console token)")
q = (
    "serverHost='developer-workstation'\n"
    "| filter process.image_name in (\"npm\", \"npm.exe\", \"npm.cmd\", "
    "\"yarn\", \"pnpm\", \"npx\")\n"
    "| filter process.command_line matches \".*(install|i|add).*\"\n"
    "| parse \"(install|i|add) $suspect_name{regex=[a-z0-9@/_.-]+}$\" "
    "from process.command_line\n"
    "| filter suspect_name = *\n"
    "| lookup known_target from npm_typosquats by suspect_name\n"
    "| filter known_target = *\n"
    "| group hosts=estimate_distinct(endpoint.name) by suspect_name, known_target\n"
    "| sort -hosts"
)
r = requests.post(f"{BASE}/api/powerQuery", headers=H,
    json={"query": q, "startTime": "24h", "priority": "low"},
    timeout=120, verify=False)
print(f"      HTTP{r.status_code}")
if r.ok:
    rows = r.json().get("values") or []
    print(f"      lookup hits: {len(rows)}")
    for row in rows[:7]:
        print(f"        {row}")
else:
    print(f"      {r.text[:300]}")
