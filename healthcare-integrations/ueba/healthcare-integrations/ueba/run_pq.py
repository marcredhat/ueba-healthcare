#!/usr/bin/env python3
"""
Run UEBA PowerQuery files against the SDL /api/powerQuery endpoint.

Why this exists: SDL Event Search UI is read-only — `| savelookup` is silently
dropped. The PowerQuery API will execute writes IF you authenticate with the
Log Write key. The default `sdl_client.power_query()` helper uses log_read,
so this runner calls `_request` directly with key_type="log_write".

Usage:
    python3 run_pq.py 01_features_auth.pq
    python3 run_pq.py 01_features_auth.pq --start 7d
    python3 run_pq.py --all                       # runs 01–05, 12 in order
    python3 run_pq.py 01_features_auth.pq --dry   # echo body, don't POST
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SDL_API_DIR = ROOT.parent.parent / "sentinelone-sdl-api"
sys.path.insert(0, str(SDL_API_DIR / "scripts"))

import sdl_client  # noqa: E402
from sdl_client import SDLClient  # noqa: E402

# Force config path
sdl_client.CONFIG_PATH = SDL_API_DIR / "config.json"

FEATURE_FILES = [
    "01_features_auth.pq",
    "02_features_endpoint.pq",
    "03_features_network.pq",
    "04_features_cloud.pq",
    "05_features_healthcare.pq",
    "12_distinct_count_features.pq",
]


def strip_comments(pq: str) -> str:
    """Strip leading '//' comment lines so the API body is just the query."""
    lines = []
    for ln in pq.splitlines():
        if ln.lstrip().startswith("//"):
            continue
        lines.append(ln)
    return "\n".join(lines).strip()


def split_into_branches(pq_text: str) -> list:
    """
    Feature-extractor file shape:
        | union
        (                          <- outer paren at col 0
            (  <leaf1 pipeline>  ),  <- leaf at col 4 (indent 4)
            (  <leaf2 pipeline>  ),
            ...
            (  <leafK pipeline>  )
        ),
        (
            (  <leafK+1>  ),
            ...
            (  <leafN>  )
        )
        | let entity_type = ..., family = ...   <- post-union tail
        | columns entity_type, entity_id, hour_ts, family, feature_name, value
        | savelookup 'ueba_features_hourly', 'merge'

    For each leaf branch we emit:  <leaf body> + <post-union tail>

    Returns list of complete queries, each <15,000 chars.
    """
    import re
    text = strip_comments(pq_text)

    # The post-union tail starts at the line after the FINAL closing paren
    # (which sits at column 0). Locate it.
    lines = text.split("\n")
    last_close = None
    for i, ln in enumerate(lines):
        if ln == ")":
            last_close = i
    if last_close is None:
        # Some files (e.g. 12) terminate the outermost union with `)`
        # possibly without a tail; fall back: tail is just savelookup.
        sl = re.search(r'\|\s*savelookup\s+[^\n]+', text)
        tail = sl.group(0) if sl else ""
    else:
        tail = "\n".join(lines[last_close + 1 :]).strip()

    # Extract every col-4 leaf paren group:  `^    (` ... `^    )`
    branches = []
    pattern = re.compile(r'^    \(\n(.*?)\n    \)', re.M | re.S)
    for m in pattern.finditer(text):
        body = m.group(1)
        # Dedent body (each line is +6 spaces for leaves inside a col-4 paren)
        body = "\n".join(ln[6:] if ln.startswith("      ") else ln for ln in body.splitlines())
        body = body.strip()
        if not body:
            continue
        # Each branch is already a complete pipeline; leave the leading filter
        # expression bare (the API accepts that). Append the tail unchanged.
        query = body
        if tail:
            query = f"{body}\n{tail}"
        branches.append(query)

    if not branches:
        return [text]
    return branches


def post_query(client: SDLClient, query: str, start_time: str) -> dict:
    import requests, urllib3  # noqa: E402
    urllib3.disable_warnings()
    url = f"{client.base_url}/api/powerQuery"
    headers = client._build_headers("log_write")
    body = {"query": query, "startTime": start_time, "priority": "low"}
    r = requests.post(url, headers=headers, json=body, timeout=120, verify=client.verify_tls)
    if not r.ok:
        return {"_http": r.status_code, "_text": r.text}
    return r.json()


def run_one(client: SDLClient, pq_file: Path, start_time: str, dry: bool) -> dict:
    raw = pq_file.read_text()
    branches = split_into_branches(raw)

    print(f"\n=== {pq_file.name} ===")
    print(f"  start_time = {start_time}")
    print(f"  branches   = {len(branches)}")
    sizes = [len(b) for b in branches]
    print(f"  sizes (chars): min={min(sizes)} max={max(sizes)} sum={sum(sizes)}")

    if dry:
        print("  (dry-run)  first branch preview:")
        print(branches[0][:600] + ("..." if len(branches[0]) > 600 else ""))
        return {"dry": True, "branches": len(branches)}

    ok = 0
    fail = 0
    total_rows = 0
    for i, q in enumerate(branches, 1):
        resp = post_query(client, q, start_time)
        if "_http" in resp:
            fail += 1
            print(f"  [{i:2d}/{len(branches)}] HTTP {resp['_http']}: {resp['_text'][:200]}")
            continue
        status = resp.get("status")
        rows = len(resp.get("values") or [])
        matching = resp.get("matchingEvents")
        total_rows += rows
        ok += 1
        # Print just the feature name (parse from `| let feature_name = "X"`)
        import re
        m = re.search(r'feature_name\s*=\s*[\'"]([^\'"]+)[\'"]', q)
        feat = m.group(1) if m else f"branch_{i}"
        print(f"  [{i:2d}/{len(branches)}] {feat:<28} status={status} rows={rows} matching={matching}")

    print(f"  --- {ok} ok, {fail} failed, {total_rows} total rows written ---")
    return {"ok": ok, "fail": fail, "rows": total_rows, "branches": len(branches)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help=".pq files to run (relative to ueba/)")
    ap.add_argument("--all", action="store_true", help="run 01–05 + 12")
    ap.add_argument("--start", default="24h", help="startTime (e.g. 24h, 7d, ISO)")
    ap.add_argument("--dry", action="store_true", help="print body, don't POST")
    args = ap.parse_args()

    if args.all:
        targets = [ROOT / f for f in FEATURE_FILES]
    elif args.files:
        targets = [ROOT / f for f in args.files]
    else:
        ap.error("supply file names or --all")

    missing = [t for t in targets if not t.exists()]
    if missing:
        sys.exit(f"missing files: {missing}")

    client = SDLClient()
    results = []
    for t in targets:
        try:
            results.append((t.name, run_one(client, t, args.start, args.dry)))
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            results.append((t.name, {"error": str(e)}))

    print("\n=== summary ===")
    for name, r in results:
        if "error" in r:
            mark = "FAIL"; detail = r["error"][:80]
        elif "dry" in r:
            mark = "DRY "; detail = f"branches={r['branches']}"
        else:
            mark = "OK  " if r.get("fail", 0) == 0 else "PART"
            detail = f"ok={r.get('ok')}/{r.get('branches')} rows={r.get('rows')}"
        print(f"  {mark}  {name}  {detail}")


if __name__ == "__main__":
    main()
