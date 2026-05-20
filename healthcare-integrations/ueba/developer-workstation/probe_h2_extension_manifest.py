#!/usr/bin/env python3
"""Diagnose why the user's H2-style extension-manifest query returns no rows.

User query:

    file.path matches ".*/Extensions/[a-p]{32}/.*/manifest\\.json$"
    | filter file.content matches (
        "\"<all_urls>\"",
        "\"webRequestBlocking\"",
        "\"cookies\"",
        "\"declarativeNetRequest\"",
        "\"scripting\""
      )
    | parse "/Extensions/$ext_id$/" from file.path
    | group n = count(), hosts = estimate_distinct(endpoint.name),
            users = estimate_distinct(actor.user.name)
        by ext_id
    | sort -n

Possible failure modes we probe for:
  1.  No manifest.json events at all in the search window (data stale).
  2.  `file.content` is not populated even though path matches
      (parser-side rewrite failed).
  3.  The synthetic ext_ids are not all-lowercase a..p, so the
      ``[a-p]{32}`` restriction filters them out.
  4.  ``filter X matches (a, b, c)`` tuple form not supported on this
      tenant — must rewrite as ``matches "a|b|c"`` or chained OR.
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


def run(label: str, query: str, window: str = "24h") -> None:
    print(f"=== {label} ===")
    print(f"  query: {query[:180]}{'…' if len(query) > 180 else ''}")
    r = requests.post(f"{B}/api/powerQuery", headers=H,
        json={"query": query, "startTime": window, "priority": "low"},
        timeout=90, verify=False)
    print(f"  HTTP{r.status_code}")
    if not r.ok:
        print(f"  ERR  {r.text[:300]}")
        print()
        return
    j = r.json()
    cols = [c["name"] for c in (j.get("columns") or [])]
    rows = j.get("values") or []
    print(f"  cols={cols}  rows={len(rows)}")
    for row in rows[:5]:
        print(f"    {row}")
    print()


SH = "serverHost='developer-workstation'"

# 1 — any manifest.json file events at all?
run("1: any manifest.json file events (24h)",
    f"{SH} | filter file.path matches '.*manifest\\\\.json$'"
    " | columns endpoint.name, file.path | limit 5")

# 2 — restrict to chrome-style /Extensions/.../manifest.json
run("2: /Extensions/.../manifest.json events",
    f"{SH} | filter file.path matches '.*/Extensions/.*manifest\\\\.json$'"
    " | columns endpoint.name, file.path | limit 5")

# 3 — is file.content populated for those events?
run("3: file.content present on manifest events",
    f"{SH} | filter file.path matches '.*/Extensions/.*manifest\\\\.json$'"
    " | filter file.content = *"
    " | columns file.path, file.content | limit 3")

# 4 — parse the ext_id directly (no [a-p] restriction)
run("4: extract ext_id (no [a-p] guard)",
    f"{SH} | filter file.path matches '.*/Extensions/.*manifest\\\\.json$'"
    " | parse '/Extensions/$ext_id$/' from file.path"
    " | filter ext_id = *"
    " | group n=count() by ext_id | sort -n | limit 5")

# 5 — does the [a-p]{32} char-class actually match the synthetic ids?
run("5: extract ext_id with [a-p]{32} guard",
    f"{SH} | filter file.path matches '.*/Extensions/[a-p]{{32}}/.*manifest\\\\.json$'"
    " | parse '/Extensions/$ext_id$/' from file.path"
    " | filter ext_id = *"
    " | group n=count() by ext_id | sort -n | limit 5")

# 6 — sensitive permissions in content (single regex, OR form)
run("6: content matches sensitive permissions (regex OR form)",
    f"{SH} | filter file.path matches '.*/Extensions/.*manifest\\\\.json$'"
    "   | filter file.content matches '.*(\"<all_urls>\"|\"webRequestBlocking\"|\"cookies\"|\"declarativeNetRequest\"|\"scripting\").*'"
    " | parse '/Extensions/$ext_id$/' from file.path"
    " | filter ext_id = *"
    " | group n=count(), hosts=estimate_distinct(endpoint.name)"
    "   by ext_id | sort -n | limit 10")

# 7 — verify user's exact tuple-form is rejected by syntax
run("7: user's tuple `matches (a,b,c)` form — is it accepted?",
    f"{SH} | filter file.path matches '.*/Extensions/.*manifest\\\\.json$'"
    "   | filter file.content matches ("
    "\"\\\"<all_urls>\\\"\","
    "\"\\\"webRequestBlocking\\\"\","
    "\"\\\"cookies\\\"\","
    "\"\\\"declarativeNetRequest\\\"\","
    "\"\\\"scripting\\\"\""
    ") | limit 3")
