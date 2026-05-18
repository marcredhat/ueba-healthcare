#!/usr/bin/env python3
"""
Validate every UEBA .pq file by submitting it to /api/powerQuery and
reporting whether the SDL parser/planner accepts it.

For multi-branch files (01-05, 12) we submit each LEAF branch separately
(reusing the splitter from run_pq.py).

For single-query files (06-11) we strip the leading comments and submit
the whole body.

Result codes:
  OK            HTTP 200, query executed
  PARSE_FAIL    HTTP 400 (typically "Don't understand", "Unknown function")
  SERVER_FAIL   HTTP 5xx
  OTHER         any other failure
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import requests
import urllib3
urllib3.disable_warnings()

ROOT = Path(__file__).resolve().parent
SDL_API_DIR = ROOT.parent.parent / "sentinelone-sdl-api"
sys.path.insert(0, str(SDL_API_DIR / "scripts"))
sys.path.insert(0, str(ROOT))

import sdl_client  # noqa: E402
sdl_client.CONFIG_PATH = SDL_API_DIR / "config.json"
from sdl_client import SDLClient  # noqa: E402

# Import the splitter from run_pq.py
from run_pq import strip_comments, split_into_branches  # noqa: E402


MULTI_BRANCH = {
    "01_features_auth.pq",
    "02_features_endpoint.pq",
    "03_features_network.pq",
    "04_features_cloud.pq",
    "05_features_healthcare.pq",
    "12_distinct_count_features.pq",
}

# Single-query files. The post-`| union` tail of multi-branch files uses
# `savelookup` which is for WRITES — to *validate* parsing we strip it
# and replace with `| limit 1` for read-only execution.
SINGLE_QUERY = {
    "06_peers_dynamic.pq": "READ_ONLY",     # multi-branch but small; treat as one
    "07_baselines_entity.pq": "READ_ONLY",
    "08_baselines_peer.pq": "READ_ONLY",
    "09_scoring.pq": "READ_ONLY",
    "09b_family_scores.pq": "READ_ONLY",
    "10_risk_daily.pq": "READ_ONLY",
    "11_alerts.pq": "READ_ONLY",
}


def submit(client: SDLClient, query: str, start: str = "1h") -> dict:
    url = f"{client.base_url}/api/powerQuery"
    headers = client._build_headers("log_read")
    body = {"query": query, "startTime": start, "priority": "low"}
    try:
        r = requests.post(url, headers=headers, json=body, timeout=90,
                          verify=client.verify_tls)
    except requests.RequestException as e:
        return {"status": "OTHER", "code": 0, "msg": str(e)[:200]}
    if r.ok:
        try:
            j = r.json()
            return {"status": "OK", "code": r.status_code,
                    "matchingEvents": j.get("matchingEvents"),
                    "rows": len(j.get("values") or [])}
        except Exception:
            return {"status": "OK", "code": r.status_code, "msg": "non-json body"}
    msg = r.text.strip()[:300]
    if 400 <= r.status_code < 500:
        return {"status": "PARSE_FAIL", "code": r.status_code, "msg": msg}
    if 500 <= r.status_code < 600:
        return {"status": "SERVER_FAIL", "code": r.status_code, "msg": msg}
    return {"status": "OTHER", "code": r.status_code, "msg": msg}


def short(q: str, n: int = 80) -> str:
    return " ".join(q.split())[:n]


def validate_file(client: SDLClient, path: Path) -> dict:
    name = path.name
    text = path.read_text()
    text_clean = strip_comments(text)

    branches: list[str]
    if name in MULTI_BRANCH:
        branches = split_into_branches(text)
        kind = f"multi-branch ({len(branches)})"
    else:
        # Single query — strip savelookup if present so we can validate
        # in read-only mode.
        q = text_clean
        # remove a trailing `| savelookup '...'` (with optional , 'mode')
        import re
        q = re.sub(r"\|\s*savelookup\s+'[^']+'\s*(?:,\s*'[^']+')?\s*$",
                   "| limit 1", q.strip())
        if "| limit" not in q.lower():
            q = q + "\n| limit 1"
        branches = [q]
        kind = "single-query"

    print(f"\n=== {name} ({kind}) ===")
    results = []
    for i, b in enumerate(branches, 1):
        r = submit(client, b)
        results.append(r)
        tag = r["status"]
        extra = ""
        if tag == "OK":
            extra = f"rows={r.get('rows', 0)}"
        else:
            extra = f"HTTP {r['code']}  {r.get('msg', '')[:200]}"
        label = f"branch {i}/{len(branches)}" if len(branches) > 1 else "query"
        print(f"  [{tag:<11}] {label:<14}  {extra}")
        if tag != "OK" and len(branches) == 1:
            # Show the failing query for single-query files
            print("  ----- failing query -----")
            for ln in b.splitlines():
                print(f"    {ln}")
            print("  -------------------------")

    ok = sum(1 for r in results if r["status"] == "OK")
    return {"name": name, "kind": kind, "ok": ok, "total": len(results),
            "results": results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*",
                    help="specific files to validate; default = all")
    args = ap.parse_args()

    pq_files = sorted(ROOT.glob("*.pq")) if not args.files else \
               [ROOT / f for f in args.files]
    client = SDLClient()
    print(f"Tenant: {client.base_url}")
    print(f"Validating {len(pq_files)} files...")

    summary = []
    for p in pq_files:
        if not p.exists():
            print(f"  MISSING  {p}")
            continue
        summary.append(validate_file(client, p))

    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"  {'file':<40} {'ok/total':>10}  status")
    print(f"  {'-'*40} {'-'*10}  ------")
    for s in summary:
        tag = "ALL OK" if s["ok"] == s["total"] else f"FAIL {s['total']-s['ok']}"
        ratio = f"{s['ok']}/{s['total']}"
        print(f"  {s['name']:<40} {ratio:>10}  {tag}")
    total_ok    = sum(s["ok"] for s in summary)
    total_total = sum(s["total"] for s in summary)
    print(f"\n  TOTAL: {total_ok}/{total_total} queries parse successfully")
    return 0 if total_ok == total_total else 1


if __name__ == "__main__":
    sys.exit(main())
