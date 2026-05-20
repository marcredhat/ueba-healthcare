#!/usr/bin/env python3
"""Probe the developer-workstation dataset on the SDL tenant to discover
exactly which field names PowerQuery sees after the parser flattens the JSON."""
from __future__ import annotations
import os, sys, requests, urllib3
from pathlib import Path

urllib3.disable_warnings()
HERE = Path(__file__).resolve().parent
SDL  = Path(os.environ.get("SDL_API_DIR", str(HERE.parent.parent / "sentinelone-sdl-api")))
sys.path.insert(0, str(SDL / "scripts"))
import sdl_client; sdl_client.CONFIG_PATH = SDL / "config.json"
from sdl_client import SDLClient

c = SDLClient()
URL = f"{c.base_url}/api/powerQuery"
H   = c._build_headers("log_read")


def run(label: str, q: str, start: str = "24h") -> None:
    r = requests.post(URL, headers=H,
        json={"query": q, "startTime": start, "priority": "low"},
        timeout=120, verify=c.verify_tls)
    print(f"\n=== {label} ===")
    if not r.ok:
        print(f"  FAIL HTTP{r.status_code}  {r.text[:300]}")
        return
    j = r.json()
    cols = [x["name"] for x in (j.get("columns") or [])]
    rows = j.get("values") or []
    print(f"  rows={len(rows)}  cols={cols}")
    for row in rows[:5]:
        print(f"    {row}")


SCOPE = "serverHost='developer-workstation'"

# Total events ingested
run("count", f"{SCOPE} | group n=count()")

# All distinct event_types
run("event_type distribution",
    f"{SCOPE} | group n=count() by event_type | sort -n")

# Try different dotted-field syntaxes
run("process.image_name (bare)",
    f"{SCOPE} | filter event_type='PROCESS_START' | group n=count() by process.image_name | sort -n | limit 10")

run("process.image_name (quoted)",
    f"{SCOPE} | filter event_type='PROCESS_START' | group n=count() by 'process.image_name' | sort -n | limit 10")

run("attributes.process.image_name",
    f"{SCOPE} | filter event_type='PROCESS_START' | group n=count() by attributes.process.image_name | sort -n | limit 10")

# What about flattened with underscore?
run("process_image_name",
    f"{SCOPE} | filter event_type='PROCESS_START' | group n=count() by process_image_name | sort -n | limit 10")

# Dump 1 raw event with all columns
run("one raw row, all columns",
    f"{SCOPE} | filter event_type='PROCESS_START' | limit 1")

# file.path probes
run("file.path bare",
    f"{SCOPE} | filter event_type='FILE_CREATE' | group n=count() by file.path | sort -n | limit 10")

run("endpoint.name bare",
    f"{SCOPE} | group n=count() by endpoint.name | sort -n | limit 10")

run("dns.query bare",
    f"{SCOPE} | filter event_type='DNS_QUERY' | group n=count() by dns.query | sort -n | limit 10")

# What if we parse from message?
run("parse process.image_name from message",
    f"{SCOPE} | filter event_type='PROCESS_START'"
    " | parse '\"image_name\": \"$img{regex=[^\"]+}$\"' from message"
    " | filter img != null"
    " | group n=count() by img | sort -n | limit 10")

run("parse file.path from message",
    f"{SCOPE} | filter event_type='FILE_CREATE'"
    " | parse '\"path\": \"$path{regex=[^\"]+}$\"' from message"
    " | filter path != null"
    " | group n=count() by path | sort -n | limit 10")

run("parse endpoint.name from message",
    f"{SCOPE}"
    " | parse '\"endpoint\": \\{\"name\": \"$host{regex=[^\"]+}$\"' from message"
    " | filter host != null"
    " | group n=count() by host | sort -n | limit 10")

# Try alternative endpoint parse (anchor on \"name\": after \"endpoint\")
run("parse endpoint.name simpler",
    f"{SCOPE}"
    " | parse '\"endpoint\": {\"name\": \"$host{regex=[^\"]+}$\"' from message"
    " | filter host != null"
    " | group n=count() by host | sort -n | limit 10")
