#!/usr/bin/env python3
"""Verify the developer-workstation generator: JSON well-formed, all 18 hunts covered."""
from __future__ import annotations
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "sample-data"))
from generate_devworkstation_events import generate_events  # noqa: E402

EXPECTED = {f"H{i}" for i in range(1, 19)}


def main() -> int:
    events = generate_events(count=600, hours_back=24, seed=42)
    print(f"Total events generated: {len(events)}")

    # 1. JSON round-trip every event
    bad = 0
    for i, e in enumerate(events):
        try:
            json.loads(json.dumps(e))
        except Exception as ex:
            bad += 1
            if bad <= 3:
                print(f"  BAD JSON at index {i}: {ex}")
    print(f"JSON round-trip: {len(events) - bad}/{len(events)} OK")

    # 2. Hunt coverage
    hunt_hits: Counter = Counter()
    scenario_hits: Counter = Counter()
    by_event_type: Counter = Counter()
    by_endpoint_os: Counter = Counter()
    for e in events:
        for h in e.get("_hunt_id", []) or []:
            hunt_hits[h] += 1
        scenario_hits[e.get("_scenario", "")] += 1
        by_event_type[e["event_type"]] += 1
        by_endpoint_os[e["endpoint"]["os"]] += 1

    print(f"\nHunts covered: {len(hunt_hits)}/18")
    for h in sorted(EXPECTED, key=lambda x: int(x[1:])):
        n = hunt_hits.get(h, 0)
        tag = "OK" if n > 0 else "MISS"
        print(f"  [{tag:>4}] {h:<4} events={n}")

    missing = EXPECTED - set(hunt_hits)
    if missing:
        print(f"\nMISSING: {sorted(missing)}")
        return 1

    print(f"\nEvent type distribution:")
    for et, n in by_event_type.most_common():
        print(f"  {et:<20} {n}")
    print(f"\nEndpoint OS distribution:")
    for os_name, n in by_endpoint_os.most_common():
        print(f"  {os_name:<20} {n}")
    print(f"\nTop 10 scenarios:")
    for sc, n in scenario_hits.most_common(10):
        print(f"  {sc:<40} {n}")

    # 3. Write a sample NDJSON file
    out = HERE / "sample.ndjson"
    with out.open("w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    print(f"\nWrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
