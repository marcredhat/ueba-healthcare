#!/usr/bin/env python3
"""
Run a UEBA feature-extractor file end-to-end, persisting all features into
ONE datatable.

Why this design:
  * SDL PowerQuery API rejects bodies >15,000 chars, so the multi-feature
    union in file 01–05 cannot be POSTed as one query.
  * `savelookup` modes (`replace` and `merge`) BOTH fully overwrite the
    target datatable on this tenant — they don't merge by key.
  * Therefore we run each union-branch as a READ query (no savelookup),
    collect all rows in Python, and write the combined payload directly to
    the config file at /datatables/<name>.json via /api/putFile.

Usage:
    python3 run_pq_combined.py 01_features_auth.pq
    python3 run_pq_combined.py 01_features_auth.pq --start 7d
    python3 run_pq_combined.py 01_features_auth.pq --table custom_name
    python3 run_pq_combined.py --all
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

ROOT = Path(__file__).resolve().parent
SDL_API_DIR = ROOT.parent.parent / "sentinelone-sdl-api"
sys.path.insert(0, str(SDL_API_DIR / "scripts"))

import sdl_client  # noqa: E402

sdl_client.CONFIG_PATH = SDL_API_DIR / "config.json"
from sdl_client import SDLClient  # noqa: E402

# Import branch splitter from sibling module
sys.path.insert(0, str(ROOT))
from run_pq import split_into_branches, strip_comments  # noqa: E402

FEATURE_FILES = [
    "01_features_auth.pq",
    "02_features_endpoint.pq",
    "03_features_network.pq",
    "04_features_cloud.pq",
    "05_features_healthcare.pq",
    "12_distinct_count_features.pq",
]
DEFAULT_TABLE = "ueba_features_hourly"


def strip_savelookup(query: str) -> str:
    """Remove the trailing `| savelookup ...` from a query so it returns rows."""
    return re.sub(r'\n\|\s*savelookup\s+[^\n]+\s*$', '', query).strip()


def post_pq(client: SDLClient, query: str, start: str, key: str = "log_read") -> dict:
    r = requests.post(
        f"{client.base_url}/api/powerQuery",
        headers=client._build_headers(key),
        json={"query": query, "startTime": start, "priority": "low"},
        timeout=120, verify=client.verify_tls,
    )
    if not r.ok:
        return {"_http": r.status_code, "_text": r.text}
    return r.json()


def put_datatable(client: SDLClient, table: str, columns: list, rows: list) -> dict:
    """Write rows to /datatables/<table> via /api/putFile."""
    path = f"/datatables/{table}"
    content = json.dumps({"columnNames": columns, "rows": rows}, default=str)

    headers = client._build_headers("config_write")
    body = {"path": path, "content": content}

    # Optional CAS guard: fetch existing version
    try:
        g = requests.post(
            f"{client.base_url}/api/getFile",
            headers=client._build_headers("config_read"),
            json={"path": path}, timeout=30, verify=client.verify_tls,
        )
        if g.ok:
            existing = g.json()
            if "version" in existing:
                body["expectedVersion"] = existing["version"]
    except Exception:
        pass

    r = requests.post(
        f"{client.base_url}/api/putFile",
        headers=headers, json=body, timeout=120, verify=client.verify_tls,
    )
    if not r.ok:
        return {"_http": r.status_code, "_text": r.text}
    return r.json()


def feature_name_of(branch: str) -> str:
    m = re.search(r'feature_name\s*=\s*[\'"]([^\'"]+)[\'"]', branch)
    return m.group(1) if m else "unknown"


def run_file(client: SDLClient, pq_file: Path, table: str, start: str, dry: bool) -> dict:
    raw = pq_file.read_text()
    branches = split_into_branches(raw)
    branches = [strip_savelookup(b) for b in branches]

    print(f"\n=== {pq_file.name} -> /datatables/{table} ===")
    print(f"  start_time = {start}")
    print(f"  branches   = {len(branches)}")
    print(f"  size (chars): min={min(len(b) for b in branches)} "
          f"max={max(len(b) for b in branches)}")

    if dry:
        print("\n  first branch preview:")
        print(branches[0][:500])
        return {"dry": True}

    # Run each branch, collect rows
    all_rows = []
    columns = None
    per_feat = []
    for i, q in enumerate(branches, 1):
        feat = feature_name_of(q)
        resp = post_pq(client, q, start, "log_read")
        if "_http" in resp:
            print(f"  [{i:2d}/{len(branches)}] {feat:<28} FAIL  HTTP {resp['_http']}  "
                  f"{resp['_text'][:200]}")
            per_feat.append((feat, 0))
            continue
        cols = [c["name"] for c in (resp.get("columns") or [])]
        vals = resp.get("values") or []
        if columns is None:
            columns = cols
        elif columns != cols:
            print(f"  [{i:2d}/{len(branches)}] {feat:<28} WARN  cols mismatch: {cols}")
        all_rows.extend(vals)
        per_feat.append((feat, len(vals)))
        print(f"  [{i:2d}/{len(branches)}] {feat:<28} rows={len(vals)} "
              f"matching={resp.get('matchingEvents')}")
        time.sleep(0.2)

    if not all_rows:
        print("  no rows produced; skipping putFile")
        return {"rows": 0}

    print(f"\n  combined: {len(all_rows)} rows across {len(per_feat)} features")
    print(f"  writing /datatables/{table} ...")
    put_resp = put_datatable(client, table, columns, all_rows)
    if "_http" in put_resp:
        print(f"  putFile FAILED HTTP {put_resp['_http']}: {put_resp['_text'][:400]}")
        return {"rows": len(all_rows), "put_error": put_resp}
    print(f"  putFile OK: {json.dumps(put_resp)[:200]}")
    return {"rows": len(all_rows), "features": per_feat, "put": put_resp}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help=".pq files to run")
    ap.add_argument("--all", action="store_true", help="run 01–05 + 12")
    ap.add_argument("--start", default="24h", help="startTime (default 24h)")
    ap.add_argument("--table", default=DEFAULT_TABLE, help="target datatable name")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    if args.all:
        targets = [ROOT / f for f in FEATURE_FILES]
    elif args.files:
        targets = [ROOT / f for f in args.files]
    else:
        ap.error("supply file names or --all")

    client = SDLClient()
    # When using --all, accumulate ALL features into one table
    if args.all:
        combined_rows = []
        combined_cols = None
        for t in targets:
            print(f"\n=== gathering {t.name} ===")
            branches = [strip_savelookup(b) for b in split_into_branches(t.read_text())]
            for i, q in enumerate(branches, 1):
                feat = feature_name_of(q)
                resp = post_pq(client, q, args.start, "log_read")
                if "_http" in resp:
                    print(f"  [{i}] {feat} FAIL HTTP {resp['_http']}")
                    continue
                cols = [c["name"] for c in (resp.get("columns") or [])]
                vals = resp.get("values") or []
                if combined_cols is None:
                    combined_cols = cols
                if cols != combined_cols:
                    print(f"  [{i}] {feat} skipped: cols mismatch {cols}")
                    continue
                combined_rows.extend(vals)
                print(f"  [{i}] {feat} rows={len(vals)}")
                time.sleep(0.2)
        print(f"\nTotal combined rows: {len(combined_rows)}")
        if combined_rows:
            r = put_datatable(client, args.table, combined_cols, combined_rows)
            print(f"putFile: {json.dumps(r)[:300]}")
    else:
        for t in targets:
            run_file(client, t, args.table, args.start, args.dry)


if __name__ == "__main__":
    main()
