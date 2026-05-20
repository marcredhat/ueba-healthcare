#!/usr/bin/env python3
"""Diagnose why the user's H3 sideloaded-extension query returns 0 rows.

Original:
    | filter event_type = "FILE_CREATE"
    | filter file.path matches ".*/Extensions/[a-p]{32}/.*"
    | filter !(process.image_name in ("chrome.exe","msedge.exe","brave.exe",
                                       "firefox.exe","Google Chrome","Microsoft Edge"))
    | let ext_id = replace(file.path, "^.*?/Extensions/([a-p]{32})/.*$", "$1")
    | group n = count() by ext_id, endpoint.name

Probable failures:
  1.  `event_type` field name not populated -> use a different column.
  2.  `let` inside a pipeline + `replace()` may not be supported.
  3.  Every browser extension manifest *is* written by the browser process,
      so the negated filter excludes everything legitimate, leaving 0.
"""
from __future__ import annotations
import json
import os
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


def run(label: str, q: str, w: str = "24h") -> None:
    print(f"=== {label} ===")
    r = requests.post(f"{B}/api/powerQuery", headers=H,
        json={"query": q, "startTime": w, "priority": "low"},
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


# 1 — does `event_type` even exist as a column?
run("1: is event_type populated?",
    f"{SH} | filter event_type = * | columns event_type, endpoint.name | limit 3")

# 2 — what process actually writes extension manifests?
run("2: writers of /Extensions/.../manifest.json",
    f"{SH} | filter file.path matches '.*/Extensions/[a-p]{{32}}/.*/manifest\\\\.json$'"
    " | group n = count() by process.image_name | sort -n | limit 10")

# 3 — does `let X = replace(...)` work?
run("3: does `let ... replace(...)` parse and run?",
    f"{SH} | filter file.path matches '.*/Extensions/[a-p]{{32}}/.*'"
    " | let ext_id = replace(file.path, '^.*?/Extensions/([a-p]{32})/.*$', '$1')"
    " | columns file.path, ext_id | limit 3")

# 4 — equivalent extraction via parse (no let/replace)
run("4: ext_id via parse",
    f"{SH} | filter file.path matches '.*/Extensions/[a-p]{{32}}/.*'"
    " | parse '/Extensions/$ext_id{regex=[a-p]{32}}$/' from file.path"
    " | filter ext_id = * | columns file.path, ext_id | limit 3")

# 5 — TRUE sideload (non-browser writer) -- semantically what H3 wants
run("5: true sideload: file writer is NOT a known browser",
    f"{SH} | filter file.path matches '.*/Extensions/[a-p]{{32}}/.*'"
    " | filter !(process.image_name in ('chrome.exe','msedge.exe','brave.exe','firefox.exe','Google Chrome','Microsoft Edge','chrome','msedge','brave','firefox'))"
    " | parse '/Extensions/$ext_id{regex=[a-p]{32}}$/' from file.path"
    " | filter ext_id = *"
    " | group n=count() by ext_id, endpoint.name, process.image_name | sort -n | limit 10")

# 6 — sideloaded marker the generator actually emits (registry / scenario tag)
run("6: scenario-tagged sideloads emitted by the generator",
    f"{SH} | filter scenario matches '.*sideload.*'"
    " | columns scenario, endpoint.name, process.image_name, file.path | limit 10")
