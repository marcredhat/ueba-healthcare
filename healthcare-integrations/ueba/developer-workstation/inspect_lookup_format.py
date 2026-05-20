#!/usr/bin/env python3
"""Compare format of an existing working UEBA datatable vs our
npm_typosquats file, to find any structural difference that makes
the lookup table resolver consider one valid and the other not."""
from __future__ import annotations
import os, sys, json
from pathlib import Path

import requests, urllib3
urllib3.disable_warnings()

HERE = Path(__file__).resolve().parent
SDL = Path(os.environ.get("SDL_API_DIR", str(HERE.parent.parent / "sentinelone-sdl-api")))
sys.path.insert(0, str(SDL / "scripts"))
import sdl_client  # noqa: E402
sdl_client.CONFIG_PATH = SDL / "config.json"
from sdl_client import SDLClient  # noqa: E402

c = SDLClient()


def get(path: str) -> dict | None:
    r = requests.post(f"{c.base_url}/api/getFile",
        headers=c._build_headers("config_read"),
        json={"path": path}, timeout=30, verify=c.verify_tls)
    if not r.ok:
        print(f"  FAIL {path}: HTTP{r.status_code} {r.text[:200]}")
        return None
    return r.json()


def show(label: str, path: str) -> None:
    j = get(path)
    if j is None:
        return
    print(f"=== {label}  ({path}) ===")
    print(f"  keys: {sorted(j.keys())}")
    if "version" in j:
        print(f"  version: {j['version']}")
    content = j.get("content", "")
    if isinstance(content, str):
        print(f"  content length: {len(content)}")
        try:
            parsed = json.loads(content)
            print(f"  parsed type: {type(parsed).__name__}")
            if isinstance(parsed, dict):
                print(f"  parsed top-level keys: {list(parsed.keys())}")
                for k, v in parsed.items():
                    if isinstance(v, list):
                        print(f"    {k} (list of {len(v)}): {str(v[:2])[:200]}")
                    else:
                        print(f"    {k}: {str(v)[:200]}")
            elif isinstance(parsed, list):
                print(f"  parsed list length: {len(parsed)}")
                if parsed:
                    print(f"  first element: {str(parsed[0])[:200]}")
        except Exception as e:
            print(f"  not JSON: {e}")
            print(f"  first 400 chars: {content[:400]}")
    print()


show("our npm_typosquats",       "/datatables/npm_typosquats")
show("UEBA smoke_test",          "/datatables/ueba_smoke_test")
show("UEBA test_default",        "/datatables/ueba_test_default")
show("UEBA peer_membership",     "/datatables/ueba_peer_membership")
show("UEBA features_hourly",     "/datatables/ueba_features_hourly")
