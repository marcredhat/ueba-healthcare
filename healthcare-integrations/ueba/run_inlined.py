#!/usr/bin/env python3
"""Submit every inlined .pq under inlined-pq/ to /api/powerQuery and
report PASS/FAIL per file. Strips comments and replaces savelookup
with `| limit 5` so we can validate read execution."""
from __future__ import annotations
import re, sys, requests, urllib3
from pathlib import Path
urllib3.disable_warnings()

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "sentinelone-sdl-api" / "scripts"))
import sdl_client
sdl_client.CONFIG_PATH = HERE.parent.parent / "sentinelone-sdl-api" / "config.json"
from sdl_client import SDLClient


def prep(q: str) -> str:
    q = "\n".join(ln for ln in q.splitlines() if not ln.lstrip().startswith("//"))
    q = re.sub(r"\|\s*savelookup\s+'[^']+'\s*(?:,\s*'[^']+')?", "| limit 5", q)
    return q.strip()


def submit(c: SDLClient, q: str) -> tuple[int, str, dict | None]:
    try:
        r = requests.post(
            f"{c.base_url}/api/powerQuery",
            headers=c._build_headers("log_read"),
            json={"query": q, "startTime": "24h", "priority": "low"},
            timeout=120, verify=c.verify_tls,
        )
    except Exception as e:
        return 0, str(e)[:200], None
    j = None
    if r.ok:
        try:
            j = r.json()
        except Exception:
            pass
    return r.status_code, r.text[:300] if not r.ok else "", j


def main() -> int:
    src = HERE / "inlined-pq"
    if not src.exists():
        print("ERROR: inlined-pq/ does not exist. Run build_inlined_pq.py first.")
        return 1

    files = sorted(p for p in src.rglob("*.pq"))
    c = SDLClient()
    print(f"Tenant: {c.base_url}")
    print(f"Validating {len(files)} inlined .pq files\n")

    by_group: dict[str, list] = {}
    for p in files:
        q = prep(p.read_text())
        code, err, j = submit(c, q)
        ok = (code == 200)
        rows = len(j.get("values") or []) if (ok and j) else 0
        group = p.parent.name if p.parent != src else "(top)"
        by_group.setdefault(group, []).append({
            "name": p.name, "ok": ok, "code": code, "rows": rows,
            "err": err, "chars": len(q),
        })

    for group, items in by_group.items():
        ok = sum(1 for x in items if x["ok"])
        print(f"=== {group}  ({ok}/{len(items)} pass)")
        for x in items:
            tag = "OK  " if x["ok"] else f"F{x['code']}"
            print(f"  [{tag}]  {x['name']:<48}  chars={x['chars']:>5}  rows={x['rows']}")
            if not x["ok"]:
                print(f"        {x['err'][:200]}")

    total = sum(len(v) for v in by_group.values())
    passed = sum(1 for v in by_group.values() for x in v if x["ok"])
    print(f"\nTOTAL: {passed}/{total} files passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
