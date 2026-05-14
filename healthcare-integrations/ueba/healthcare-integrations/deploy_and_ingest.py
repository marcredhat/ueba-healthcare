#!/usr/bin/env python3
"""
Deploy Avelios Medical + Omniconnect parsers to SDL, ingest sample events,
verify OCSF enrichment via PowerQuery.

Uses the shared SDLClient from shared/sentinelone-sdl-api/scripts/sdl_client.py
(reads creds from shared/sentinelone-sdl-api/config.json).
"""
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SDL_API_DIR = ROOT.parent / "sentinelone-sdl-api"
sys.path.insert(0, str(SDL_API_DIR / "scripts"))

# Force SDLClient to load config.json from sentinelone-sdl-api
from sdl_client import SDLClient, CONFIG_PATH  # noqa: E402

# Override the module-level CONFIG_PATH used by SDLClient
import sdl_client  # noqa: E402
sdl_client.CONFIG_PATH = SDL_API_DIR / "config.json"

sys.path.insert(0, str(ROOT / "avelios-medical" / "sample-data"))
sys.path.insert(0, str(ROOT / "omniconnect" / "sample-data"))
from generate_avelios_events import generate_events as gen_avelios  # noqa: E402
from generate_omniconnect_events import generate_events as gen_omniconnect  # noqa: E402

DATASETS = [
    {
        "key":         "avelios",
        "name":        "Avelios Medical",
        "parser":      "Avelios-Medical-OCSF",
        "parser_file": ROOT / "avelios-medical" / "parsers" / "avelios-medical.conf",
        "server_host": "avelios-medical",
        "log_file":    "avelios-medical.json",
        "generator":   gen_avelios,
    },
    {
        "key":         "omniconnect",
        "name":        "Omniconnect",
        "parser":      "Omniconnect-OCSF",
        "parser_file": ROOT / "omniconnect" / "parsers" / "omniconnect.conf",
        "server_host": "omniconnect",
        "log_file":    "omniconnect.json",
        "generator":   gen_omniconnect,
    },
]


def deploy_parser(c: SDLClient, ds: dict) -> None:
    body = ds["parser_file"].read_text()
    path = f"/logParsers/{ds['parser']}"

    # CAS guard - get existing version if present
    expected_version = None
    try:
        existing = c.get_file(path)
        expected_version = existing.get("version")
    except Exception:
        pass

    c.put_file(path, body, expected_version=expected_version)
    print(f"  [OK] deployed {path} ({len(body)} bytes)")


def ingest_events(c: SDLClient, ds: dict, count: int, hours: int) -> int:
    events = ds["generator"](count, hours)
    session = f"{ds['key']}-{uuid.uuid4().hex[:8]}"

    # Convert to addEvents format
    now_ns = int(time.time() * 1_000_000_000)
    formatted = []
    for i, evt in enumerate(events):
        # attrs go as flat key/values; nested objects are preserved as JSON strings
        # but the parser uses `format: "$=json{parse=json}$"` against `message`,
        # so we put the raw JSON as `message` to let the parser flatten it.
        formatted.append({
            "ts":   str(now_ns + i * 1_000_000),  # 1ms spacing
            "sev":  3,
            "attrs": {
                "message": json.dumps(evt),
            }
        })

    # Send in batches of 500 to stay well under 5MB / request
    batch_size = 500
    sent = 0
    for i in range(0, len(formatted), batch_size):
        batch = formatted[i:i+batch_size]
        c.add_events(
            session=session,
            events=batch,
            session_info={
                "serverHost": ds["server_host"],
                "logfile":    ds["log_file"],
                "parser":     ds["parser"],
            },
        )
        sent += len(batch)
    print(f"  [OK] ingested {sent} events as serverHost='{ds['server_host']}' parser='{ds['parser']}'")
    return sent


def verify(c: SDLClient, ds: dict) -> None:
    print(f"  [..] waiting 15s for indexing...")
    time.sleep(15)

    host = f"serverHost='{ds['server_host']}'"
    checks = [
        ("total events ingested",        f"{host}"),
        ("OCSF metadata.vendor present", f"{host} dataSource.vendor='{ds['name']}'" if ds['name'] != 'Avelios Medical' else f"{host} dataSource.vendor='Avelios'"),
        ("OCSF class_uid populated",     f"{host} class_uid != null"),
        ("OCSF severity_id populated",   f"{host} severity_id != null"),
        ("Security findings (cat 2)",    f"{host} category_uid='2'"),
    ]
    passed = 0
    for label, q in checks:
        try:
            r = c.power_query(query=q + " | columns event_id | limit 1", start_time="10m")
            n = int(r.get("matchingEvents") or 0)
            tag = "PASS" if n >= 1 else "FAIL"
            if n >= 1:
                passed += 1
            print(f"    {tag}  {label:<35s} ({n} matches)")
        except Exception as e:
            print(f"    ERR   {label}  -> {str(e)[:120]}")

    # Per-category breakdown
    try:
        q = f"{host} | group ct=count() by event_category, class_uid, class_name | sort -ct"
        r = c.power_query(query=q, start_time="10m")
        print(f"\n    Per-category breakdown ({ds['name']}):")
        cols = r.get("columns") or []
        print(f"      {cols}")
        for row in (r.get("values") or [])[:15]:
            print(f"      {row}")
    except Exception as e:
        print(f"    breakdown ERR: {str(e)[:120]}")
    print(f"\n  Coverage: {passed}/{len(checks)} OCSF checks passed")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--count",   type=int, default=100, help="events per source (default 100)")
    ap.add_argument("--hours",   type=int, default=24,  help="history hours (default 24)")
    ap.add_argument("--source",  choices=["avelios", "omniconnect", "all"], default="all")
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args()

    c = SDLClient()
    print(f"Connected: {c.base_url}\n")

    targets = DATASETS if args.source == "all" else [d for d in DATASETS if d["key"] == args.source]

    for ds in targets:
        print(f"{'='*70}\n{ds['name']}\n{'='*70}")
        print("STEP 1 - Deploy parser")
        deploy_parser(c, ds)
        print("\nSTEP 2 - Ingest sample events")
        ingest_events(c, ds, args.count, args.hours)
        if not args.no_verify:
            print("\nSTEP 3 - Verify OCSF enrichment via PowerQuery")
            verify(c, ds)
        print()

    print("="*70)
    print("DONE")
    print("="*70)
    print("\nView in AI SIEM:")
    print(f"  {c.base_url}/#/search")
    print("\nExample PowerQueries:")
    for ds in targets:
        print(f"  serverHost='{ds['server_host']}' | limit 20")
    print("  serverHost='avelios-medical' or serverHost='omniconnect' | group ct=count() by event_category | sort -ct")


if __name__ == "__main__":
    sys.exit(main() or 0)
