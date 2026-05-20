#!/usr/bin/env python3
"""Run the user's exact H18 burst-install query and report failure mode.

If 0 rows: try progressively-relaxed forms to isolate which clause kills
the result.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import requests, urllib3

# --- portable SDL_API_DIR resolution -----------------------------------
def _default_sdl_dir() -> str:
    """Locate ../../sentinelone-sdl-api relative to this script."""
    import pathlib as _p
    return str(_p.Path(__file__).resolve().parent.parent.parent / 'sentinelone-sdl-api')
urllib3.disable_warnings()

cfg = json.load(open(os.environ.get("SDL_API_DIR",
    _default_sdl_dir()) + "/config.json"))
H = {"Authorization": f"Bearer {cfg['console_api_token']}",
     "Content-Type":  "application/json"}
B = cfg["base_url"].rstrip("/")


def run(label: str, q: str, w: str = "24h") -> None:
    r = requests.post(f"{B}/api/powerQuery", headers=H,
        json={"query": q, "startTime": w, "priority": "low"},
        timeout=120, verify=False)
    print(f"\n=== {label} ===  HTTP{r.status_code}")
    if not r.ok:
        print(f"  {r.text[:300]}")
        return
    j = r.json()
    cols = [c["name"] for c in (j.get("columns") or [])]
    rows = j.get("values") or []
    print(f"  cols={cols}  rows={len(rows)}")
    for row in rows[:10]:
        print("  ", row)


SH = "serverHost='developer-workstation'"

# A — the user's exact query (image_name list does NOT include .exe / .cmd)
USER_Q = (
    f"{SH}\n"
    '| filter process.image_name in ("npm", "yarn", "pnpm", "npx")\n'
    '| filter process.command_line matches ".*(^|\\\\s)install(\\\\s|$).*"\n'
    '| parse "install $pkg{regex=[a-z0-9@/_.-]+}$" from process.command_line\n'
    '| filter pkg = *\n'
    '| group\n'
    '    hosts      = estimate_distinct(endpoint.name),\n'
    '    users      = estimate_distinct(actor.user.name),\n'
    '    first_seen = min(timestamp),\n'
    '    last_seen  = max(timestamp)\n'
    "  by pkg, bucket_30m = timebucket('30 minutes')\n"
    '| filter hosts >= 5\n'
    '| let span_min = (last_seen - first_seen) / 60000000000\n'
    '| filter span_min < 30\n'
    '| sort -hosts'
)
run("A: user's exact query", USER_Q)

# B — drop the span_min filter only (keep hosts >= 5)
run("B: drop span_min<30 (just hosts >= 5 per 30m bucket)",
    f"{SH}\n"
    '| filter process.image_name in ("npm", "yarn", "pnpm", "npx")\n'
    '| filter process.command_line matches ".*(^|\\\\s)install(\\\\s|$).*"\n'
    '| parse "install $pkg{regex=[a-z0-9@/_.-]+}$" from process.command_line\n'
    '| filter pkg = *\n'
    '| group hosts = estimate_distinct(endpoint.name),\n'
    '         first_seen=min(timestamp), last_seen=max(timestamp)\n'
    "   by pkg, bucket_30m = timebucket('30 minutes')\n"
    '| filter hosts >= 5\n'
    '| sort -hosts')

# C — broaden image_name to include .exe / .cmd (real synthetic data has those)
run("C: broadened image_name list (npm.exe, npm.cmd, ...)",
    f"{SH}\n"
    '| filter process.image_name in ("npm","npm.exe","npm.cmd","yarn","yarn.exe","pnpm","pnpm.exe","npx","npx.exe")\n'
    '| filter process.command_line matches ".*(^|\\\\s)install(\\\\s|$).*"\n'
    '| parse "install $pkg{regex=[a-z0-9@/_.-]+}$" from process.command_line\n'
    '| filter pkg = *\n'
    '| group hosts = estimate_distinct(endpoint.name),\n'
    '         first_seen=min(timestamp), last_seen=max(timestamp)\n'
    "   by pkg, bucket_30m = timebucket('30 minutes')\n"
    '| filter hosts >= 5\n'
    '| sort -hosts')

# D — full corrected query: broad image_name + span<30 + hosts>=5
run("D: corrected H18 (broad image_name + span+hosts thresholds)",
    f"{SH}\n"
    '| filter process.image_name in ("npm","npm.exe","npm.cmd","yarn","yarn.exe","pnpm","pnpm.exe","npx","npx.exe")\n'
    '| filter process.command_line matches ".*(^|\\\\s)install(\\\\s|$).*"\n'
    '| parse "install $pkg{regex=[a-z0-9@/_.-]+}$" from process.command_line\n'
    '| filter pkg = *\n'
    '| group hosts = estimate_distinct(endpoint.name),\n'
    '         users = estimate_distinct(actor.user.name),\n'
    '         first_seen=min(timestamp), last_seen=max(timestamp)\n'
    "   by pkg, bucket_30m = timebucket('30 minutes')\n"
    '| filter hosts >= 5\n'
    '| let span_min = (last_seen - first_seen) / 60000000000\n'
    '| filter span_min < 30\n'
    '| sort -hosts')
