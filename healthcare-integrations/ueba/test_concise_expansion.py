#!/usr/bin/env python3
"""Verify the concise `let base = ( ... )` form in 01_features_auth.pq
expands and runs successfully via the splitter + API."""
from __future__ import annotations
import sys, json, requests, urllib3
from pathlib import Path
urllib3.disable_warnings()

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SDL_API = HERE.parent.parent / "sentinelone-sdl-api"
sys.path.insert(0, str(SDL_API / "scripts"))

import sdl_client
sdl_client.CONFIG_PATH = SDL_API / "config.json"
from sdl_client import SDLClient
from run_pq import strip_comments, _expand_let_base, split_into_branches

src = (HERE / "01_features_auth.pq").read_text()
clean = strip_comments(src)
expanded = _expand_let_base(clean)
print(f"source       : {len(src):>6} chars")
print(f"stripped     : {len(clean):>6} chars")
print(f"expanded     : {len(expanded):>6} chars  (after let-base inlining)")

branches = split_into_branches(src)
print(f"branches     : {len(branches)}")
print(f"branch sizes : min={min(len(b) for b in branches)}  "
      f"max={max(len(b) for b in branches)}  "
      f"avg={sum(len(b) for b in branches)//len(branches)}")

c = SDLClient()

def submit(q):
    r = requests.post(f"{c.base_url}/api/powerQuery",
        headers=c._build_headers("log_read"),
        json={"query": q, "startTime": "2h", "priority": "low"},
        timeout=60, verify=c.verify_tls)
    return r.status_code, r.text[:400], (r.json() if r.ok else None)

print("\n--- branch 1 preview (first 600 chars) ---")
print(branches[0][:600])
print("--- end preview ---\n")

# Submit each branch and report status
ok = 0; rows = 0
for i, b in enumerate(branches, 1):
    code, txt, j = submit(b)
    if code == 200:
        n = len(j.get("values") or [])
        rows += n
        ok += 1
        print(f"  [OK]  branch {i:2}  rows={n}")
    else:
        print(f"  [FAIL HTTP {code}] branch {i}")
        print(f"     {txt[:300]}")

print(f"\nSUMMARY: {ok}/{len(branches)} branches passed, {rows} total rows")
