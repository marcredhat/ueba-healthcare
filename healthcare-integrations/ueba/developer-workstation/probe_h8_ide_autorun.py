#!/usr/bin/env python3
"""Diagnose H8: IDE-spawned task/script autorun on workspace open.

User query:
    | filter process.parent.image_name in ("Code.exe","code","cursor","windsurf")
    | parse "--folder-uri[= ]+$folder{regex=[^ ]+}$" from process.parent.command_line
    | filter folder = *
    | filter process.image_name in ("powershell.exe","pwsh.exe","cmd.exe","bash","sh")
    | filter (timestamp - process.parent.start_time) < 30000000000
    | columns timestamp, endpoint.name, actor.user.name, folder,
              process.command_line, process.parent.command_line
    | sort -timestamp

Suspected blockers in order of likelihood:
  1.  process.parent.start_time is NOT emitted by the generator and not
      mapped by the parser → the time-window filter excludes everything.
  2.  process.parent.image_name not populated (parser flattening issue).
  3.  process.parent.command_line not populated.
  4.  The parse regex never matches because `--folder-uri` is on the
      child command_line, not the parent.
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

SDL = Path(os.environ.get("SDL_API_DIR",
    _default_sdl_dir()))
cfg = json.load(open(SDL / "config.json"))
H = {"Authorization": f"Bearer {cfg['console_api_token']}",
     "Content-Type":  "application/json"}
B = cfg["base_url"].rstrip("/")
SH = "serverHost='developer-workstation'"


def run(label, q, w="24h"):
    print(f"=== {label} ===")
    r = requests.post(f"{B}/api/powerQuery", headers=H,
        json={"query": q, "startTime": w, "priority":"low"},
        timeout=90, verify=False)
    print(f"  HTTP{r.status_code}")
    if not r.ok:
        print(f"  ERR  {r.text[:300]}\n")
        return
    j=r.json(); cols=[c["name"] for c in (j.get("columns") or [])]; rows=j.get("values") or []
    print(f"  cols={cols}  rows={len(rows)}")
    for row in rows[:5]: print(f"    {row}")
    print()


# 1 — IDE parent processes present at all
run("1: events where process.parent.image_name is an IDE",
    f"{SH} | filter process.parent.image_name in ('Code.exe','code','cursor','windsurf','Code','Cursor','Windsurf')"
    " | columns process.parent.image_name, process.image_name, process.parent.command_line | limit 5")

# 2 — does process.parent.start_time even exist?
run("2: is process.parent.start_time populated anywhere?",
    f"{SH} | filter process.parent.start_time = * | columns process.parent.start_time | limit 3")

# 3 — drop the time-window filter and see IDE-spawned shells
run("3: IDE-spawned shells (no start_time guard)",
    f"{SH} | filter process.parent.image_name in ('Code.exe','code','cursor','windsurf','Code','Cursor','Windsurf')"
    " | filter process.image_name in ('powershell.exe','pwsh.exe','cmd.exe','bash','sh','zsh')"
    " | columns endpoint.name, process.parent.image_name, process.parent.command_line, process.image_name, process.command_line | limit 10")

# 4 — does --folder-uri appear on parent.command_line?
run("4: --folder-uri occurrences (anywhere)",
    f"{SH} | filter process.parent.command_line matches '.*--folder-uri.*'"
    " | columns process.parent.image_name, process.parent.command_line | limit 5")

# 5 — scenario tag the generator emits for this hunt
run("5: hunt H8 scenario events emitted",
    f"{SH} | filter _hunt_id matches '.*H8.*'"
    " | columns scenario, endpoint.name, process.parent.image_name, process.image_name, process.command_line | limit 10")
