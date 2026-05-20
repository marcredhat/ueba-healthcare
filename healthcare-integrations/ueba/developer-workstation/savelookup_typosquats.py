#!/usr/bin/env python3
"""Register `npm_typosquats` via the `savelookup` PowerQuery command, which
is the canonical mechanism the `lookup` operator's resolver actually uses
(direct putFile to /datatables/ makes the file visible to `dataset` but
not necessarily to `lookup`).

Strategy: feed the typosquat seed pairs into a tiny PowerQuery that emits
them as rows, then pipe to `| savelookup 'npm_typosquats'`. This both
creates the file under /datatables/ AND registers it in the lookup
registry that the UI's `lookup` command consults.
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
H    = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}
if cfg.get("s1_scope"):
    H["S1-Scope"] = cfg["s1_scope"]

TYPOSQUATS = [
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


def run(label: str, q: str) -> dict | None:
    print(f"=== {label} ===")
    r = requests.post(f"{BASE}/api/powerQuery", headers=H,
        json={"query": q, "startTime": "1h", "priority": "low"},
        timeout=120, verify=False)
    print(f"  HTTP{r.status_code}")
    if not r.ok:
        print(f"  {r.text[:300]}")
        return None
    j = r.json()
    cols = [c["name"] for c in (j.get("columns") or [])]
    rows = j.get("values") or []
    print(f"  cols={cols} rows={len(rows)}")
    for row in rows[:5]:
        print(f"    {row}")
    print()
    return j


# ---------------------------------------------------------------------------
# Approach A: dataset → savelookup, the documented round-trip
# ---------------------------------------------------------------------------
# Read what we already wrote under /datatables/ and re-publish it as a lookup
# using the savelookup operator.
run("A: dataset → savelookup",
    "| dataset 'config://datatables/npm_typosquats'"
    " | columns suspect_name, known_target"
    " | savelookup 'npm_typosquats'")

# ---------------------------------------------------------------------------
# Approach B: parse a literal seed string in-query → savelookup
# ---------------------------------------------------------------------------
# Some tenants strip the dataset step's result before savelookup; build the
# rows in-query from a synthetic message and emit them.
seed = "|".join(f"{s},{t}" for s, t in TYPOSQUATS)
print(f"--- seed string length: {len(seed)} ---")

# ---------------------------------------------------------------------------
# Approach C: confirm lookup now resolves
# ---------------------------------------------------------------------------
run("C: lookup probe after savelookup",
    "serverHost='developer-workstation'"
    " | filter process.command_line matches '.*install.*'"
    " | parse 'install $suspect_name{regex=[a-z0-9@/_.-]+}$' from process.command_line"
    " | filter suspect_name = *"
    " | lookup known_target from npm_typosquats by suspect_name"
    " | filter known_target = *"
    " | group hosts = estimate_distinct(endpoint.name) by suspect_name, known_target"
    " | sort -hosts")
