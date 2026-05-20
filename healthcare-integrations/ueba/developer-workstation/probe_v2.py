#!/usr/bin/env python3
"""After the parser was extended with explicit field extraction,
verify that endpoint_name / process_image_name / parent_image_name /
file_path / dns_query are populated."""
import os, sys, requests, urllib3, time
from pathlib import Path
urllib3.disable_warnings()
HERE = Path(__file__).resolve().parent
SDL = Path(os.environ.get("SDL_API_DIR", str(HERE.parent.parent / "sentinelone-sdl-api")))
sys.path.insert(0, str(SDL / "scripts"))
import sdl_client; sdl_client.CONFIG_PATH = SDL / "config.json"
from sdl_client import SDLClient

c = SDLClient(); URL = f"{c.base_url}/api/powerQuery"; H = c._build_headers("log_read")

def run(label, q, start="24h"):
    r = requests.post(URL, headers=H,
        json={"query": q, "startTime": start, "priority": "low"},
        timeout=120, verify=c.verify_tls)
    print(f"\n=== {label} ===")
    if not r.ok: print(f"  FAIL HTTP{r.status_code}: {r.text[:300]}"); return
    j = r.json()
    cols = [x["name"] for x in (j.get("columns") or [])]
    rows = j.get("values") or []
    print(f"  rows={len(rows)} cols={cols}")
    for row in rows[:5]: print(f"    {row}")

SCOPE = "serverHost='developer-workstation'"

# Wait a bit for indexing
print("Waiting 10s for full indexing...")
time.sleep(10)

run("endpoint_name", f"{SCOPE} | group n=count() by endpoint_name | sort -n | limit 10")
run("process_image_name PROCESS_START", f"{SCOPE} | filter event_type='PROCESS_START' | group n=count() by process_image_name | sort -n | limit 15")
run("parent_image_name PROCESS_START", f"{SCOPE} | filter event_type='PROCESS_START' | group n=count() by parent_image_name | sort -n | limit 15")
run("file_path FILE_CREATE", f"{SCOPE} | filter event_type='FILE_CREATE' | group n=count() by file_path | sort -n | limit 10")
run("dns_query", f"{SCOPE} | filter event_type='DNS_QUERY' | group n=count() by dns_query | sort -n | limit 15")
run("scenario", f"{SCOPE} | group n=count() by scenario | sort -n | limit 15")
