#!/usr/bin/env python3
"""One-shot, idempotent creator for the `npm_typosquats` dataset.

Performs both steps SDL needs so the table is reachable from *both*
PowerQuery operators that touch it:

  1.  putFile  /datatables/npm_typosquats          -> queryable via
                                                     ``| dataset 'config://datatables/npm_typosquats'``
  2.  | savelookup 'npm_typosquats'                -> registers the bare
                                                     name in the lookup
                                                     registry so
                                                     ``| lookup ... from npm_typosquats by ...``
                                                     resolves in the UI.

Re-runs are safe: the putFile uses CAS via ``expectedVersion`` and the
savelookup overwrites the named entry.
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
TOK  = cfg.get("console_api_token") or cfg.get("config_write_key")
if not TOK:
    sys.exit("ERROR: console_api_token (or config_write_key) missing in config.json")

H = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}
if cfg.get("s1_scope"):
    H["S1-Scope"] = cfg["s1_scope"]

print(f"Tenant : {BASE}")
print(f"Scope  : {cfg.get('s1_scope') or '(token default)'}")
print()

# ---------------------------------------------------------------------------
# 25 known npm typosquat -> canonical mappings
# ---------------------------------------------------------------------------
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

PATH = "/datatables/npm_typosquats"
CONTENT = json.dumps({
    "columnNames": ["suspect_name", "known_target"],
    "rows":        [list(p) for p in TYPOSQUATS],
})


def post(api: str, body: dict, timeout: int = 60) -> requests.Response:
    return requests.post(f"{BASE}/api{api}", headers=H,
                         json=body, timeout=timeout, verify=False)


# ---------------------------------------------------------------------------
# STEP 1 — putFile  (so `dataset 'config://datatables/npm_typosquats'` works)
# ---------------------------------------------------------------------------
print(f"[1/3] putFile {PATH}  ({len(TYPOSQUATS)} rows)")
g = post("/getFile", {"path": PATH}, timeout=30)
version = g.json().get("version") if g.ok else None
print(f"      existing version: {version}")

body = {"path": PATH, "content": CONTENT, "prettyprint": True}
if version is not None:
    body["expectedVersion"] = version
p = post("/putFile", body, timeout=60)
print(f"      HTTP{p.status_code}  {p.text[:160]}")
if not p.ok:
    sys.exit("FAIL: putFile rejected")

# ---------------------------------------------------------------------------
# STEP 2 — savelookup  (so `lookup ... from npm_typosquats` works in the UI)
# ---------------------------------------------------------------------------
print(f"\n[2/3] savelookup 'npm_typosquats'")
q = (
    "| dataset 'config://datatables/npm_typosquats'"
    " | columns suspect_name, known_target"
    " | savelookup 'npm_typosquats'"
)
r = post("/powerQuery", {"query": q, "startTime": "5m", "priority": "low"},
         timeout=120)
print(f"      HTTP{r.status_code}")
if r.ok:
    rows = r.json().get("values") or []
    for row in rows:
        print(f"      registered: {row}")
else:
    sys.exit(f"FAIL: savelookup rejected — {r.text[:300]}")

# ---------------------------------------------------------------------------
# STEP 3 — round-trip verification via the *lookup* operator
# ---------------------------------------------------------------------------
print(f"\n[3/3] verify `lookup` resolves the name")
q = (
    "serverHost='developer-workstation'"
    " | filter process.image_name in (\"npm\", \"npm.exe\", \"npm.cmd\","
    " \"yarn\", \"pnpm\", \"npx\")"
    " | filter process.command_line matches \".*(^|\\\\s)(install|i|add)(\\\\s|$).*\""
    " | parse \"(install|i|add) $suspect_name{regex=[a-z0-9@/_.-]+}$\""
    "  from process.command_line"
    " | filter suspect_name = *"
    " | lookup known_target from npm_typosquats by suspect_name"
    " | filter known_target = *"
    " | group hosts = estimate_distinct(endpoint.name)"
    "   by suspect_name, known_target"
    " | sort -hosts"
)
r = post("/powerQuery", {"query": q, "startTime": "24h", "priority": "low"},
         timeout=120)
print(f"      HTTP{r.status_code}")
if r.ok:
    rows = r.json().get("values") or []
    print(f"      lookup hits: {len(rows)}")
    for row in rows[:10]:
        print(f"        {row}")
    if not rows:
        print("      (no hits — make sure synthetic dev-workstation"
              " events are present in the last 24h)")
else:
    print(f"      {r.text[:300]}")
