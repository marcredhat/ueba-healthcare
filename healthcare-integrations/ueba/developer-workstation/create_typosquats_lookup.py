#!/usr/bin/env python3
"""Create the npm_typosquats lookup datatable that hunt H15 depends on.

Each row maps a known typosquat package name to its legitimate target.
In a real SOC this list is regenerated daily from npm's most-downloaded
list using a Levenshtein library; here we seed it with the typosquats
already used by the synthetic generator plus a handful of public ones.
"""
from __future__ import annotations
import json, os, sys, requests, urllib3
from pathlib import Path
urllib3.disable_warnings()
HERE = Path(__file__).resolve().parent
SDL = Path(os.environ.get("SDL_API_DIR", str(HERE.parent.parent / "sentinelone-sdl-api")))
sys.path.insert(0, str(SDL / "scripts"))
import sdl_client; sdl_client.CONFIG_PATH = SDL / "config.json"
from sdl_client import SDLClient

c = SDLClient()

# (suspect_name, known_target) pairs — the synthetic generator emits the first
# four, the rest are real-world examples observed in the wild.
TYPOSQUATS: list[tuple[str, str]] = [
    ("expres",        "express"),
    ("loadash",       "lodash"),
    ("colorss",       "colors"),
    ("requesst",      "request"),
    ("eslint-config-airbnb-pro", "eslint-config-airbnb"),
    ("event-stream-helper",      "event-stream"),
    ("ua-parser-utils",          "ua-parser-js"),
    ("lodash-utils",  "lodash"),
    ("lodaash",       "lodash"),
    ("expresss",      "express"),
    ("axios-lib",     "axios"),
    ("axioss",        "axios"),
    ("reactt",        "react"),
    ("react-utility", "react"),
    ("vuetify-utils", "vuetify"),
    ("commaander",    "commander"),
    ("yargs-plus",    "yargs"),
    ("chalkk",        "chalk"),
    ("chalk-cli",     "chalk"),
    ("nextt",         "next"),
    ("webpackk",      "webpack"),
    ("typescriptt",   "typescript"),
    ("debugg",        "debug"),
    ("moment-tz",     "moment"),
    ("uuid-gen",      "uuid"),
]

path = "/datatables/npm_typosquats"
columns = ["suspect_name", "known_target"]
rows = [list(p) for p in TYPOSQUATS]
content = json.dumps({"columnNames": columns, "rows": rows})

# CAS guard
body = {"path": path, "content": content}
try:
    g = requests.post(f"{c.base_url}/api/getFile",
        headers=c._build_headers("config_read"),
        json={"path": path}, timeout=30, verify=c.verify_tls)
    if g.ok:
        body["expectedVersion"] = g.json().get("version")
except Exception:
    pass

r = requests.post(f"{c.base_url}/api/putFile",
    headers=c._build_headers("config_write"),
    json=body, timeout=60, verify=c.verify_tls)
print(f"HTTP{r.status_code}: {r.text[:200]}")
print(f"Wrote {len(rows)} rows to {path}")
