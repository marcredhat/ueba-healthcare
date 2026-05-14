#!/usr/bin/env python3
"""
Produce hourly-rotated, gzipped NDJSON log files for Avelios Medical and
Omniconnect — the format an S3-compatible bucket is most likely to hold.

Output layout (under raw-logs/):
  avelios-medical/
    YYYY/MM/DD/avelios-medical.YYYY-MM-DD-HH.ndjson.gz   (one file per hour)
  omniconnect/
    YYYY/MM/DD/omniconnect.YYYY-MM-DD-HH.ndjson.gz
"""
import gzip
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC  = ROOT.parent
sys.path.insert(0, str(SRC / "avelios-medical" / "sample-data"))
sys.path.insert(0, str(SRC / "omniconnect" / "sample-data"))
from generate_avelios_events import generate_events as gen_avelios   # noqa: E402
from generate_omniconnect_events import generate_events as gen_omniconnect  # noqa: E402

SOURCES = [
    ("avelios-medical", gen_avelios,     500),  # events per source over 24h
    ("omniconnect",     gen_omniconnect, 500),
]


def write_rotated(source: str, events: list) -> int:
    buckets: dict = defaultdict(list)
    for evt in events:
        ts = datetime.strptime(evt["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")
        key = (ts.year, ts.month, ts.day, ts.hour)
        buckets[key].append(evt)

    written = 0
    for (y, m, d, h), evts in sorted(buckets.items()):
        out_dir = ROOT / source / f"{y:04d}" / f"{m:02d}" / f"{d:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{source}.{y:04d}-{m:02d}-{d:02d}-{h:02d}.ndjson.gz"
        out = out_dir / fname
        with gzip.open(out, "wt", encoding="utf-8") as f:
            for evt in evts:
                f.write(json.dumps(evt) + "\n")
        written += 1
        print(f"  {out.relative_to(ROOT)}   ({len(evts)} events)")
    return written


def main() -> int:
    for source, gen, count in SOURCES:
        print(f"\n=== {source} — generating {count} events over 24h ===")
        events = gen(count, 24)
        files = write_rotated(source, events)
        print(f"  -> {files} hourly files written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
