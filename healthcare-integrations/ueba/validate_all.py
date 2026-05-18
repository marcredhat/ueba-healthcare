#!/usr/bin/env python3
"""Validate every .pq under inlined-pq/ by submitting it to
/api/powerQuery with savelookup stripped. Reports PASS/FAIL per file."""
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


def main() -> int:
    src = HERE / "inlined-pq"
    files = sorted(src.rglob("*.pq"))
    c = SDLClient()
    print(f"Tenant: {c.base_url}")
    print(f"Validating {len(files)} files\n")

    pass_n = fail_n = 0
    fails: list[tuple[str, int, str]] = []
    for p in files:
        q = prep(p.read_text())
        try:
            r = requests.post(
                f"{c.base_url}/api/powerQuery",
                headers=c._build_headers("log_read"),
                json={"query": q, "startTime": "24h", "priority": "low"},
                timeout=120, verify=c.verify_tls,
            )
            ok = r.ok
            code = r.status_code
            err = r.text[:200] if not ok else ""
        except Exception as e:
            ok, code, err = False, 0, str(e)[:200]

        rel = str(p.relative_to(src))
        if ok:
            pass_n += 1
            print(f"  PASS  {rel}")
        else:
            fail_n += 1
            fails.append((rel, code, err))
            print(f"  FAIL  {rel}  HTTP {code}")

    print(f"\n{'='*72}")
    print(f"SUMMARY: {pass_n} PASS  /  {fail_n} FAIL  /  {len(files)} total")
    if fails:
        print("\nFailures:")
        for rel, code, err in fails:
            print(f"  {rel}  HTTP {code}\n     {err}\n")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
