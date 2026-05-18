#!/usr/bin/env python3
"""
Refactor 12_distinct_count_features.pq:

Original form uses `let NAME = (subquery); ... | union NAME1, NAME2, ...`
which depends on `let X = (subquery)` aliasing — NOT supported in SDL.

Each subquery is already self-contained (its own parse + 2-stage group +
columns emitting the final schema), so the fix is mechanical: strip the
`let NAME = (...)` wrappers and place each pipeline as a union branch.
Branches are chunked into nested unions to respect the 10-per-union limit.
"""
import os, re, sys

PATH = "12_distinct_count_features.pq"
CHUNK = 10

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    src = open(PATH).read()

    # Drop any PENDING REFACTOR header
    src = re.sub(r'\A// PENDING REFACTOR.*?(?=\n//\s*12_|\nlet\s+\w)', '', src, flags=re.S)

    # Extract each `let NAME = (\n   <body>\n  );` block
    bodies = []
    for m in re.finditer(r'let\s+\w+\s*=\s*\n\s*\(\s*\n(.*?)\n\s*\)\s*;', src, re.S):
        bodies.append(m.group(1).rstrip())

    if not bodies:
        print(f"  no let-blocks found in {PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"  extracted {len(bodies)} self-contained subqueries")

    def branch(body: str) -> str:
        # Indent body 6 spaces for placement inside `    ( ... )`
        indented = "\n".join(("      " + ln) if ln.strip() else ln for ln in body.split("\n"))
        return f"    (\n{indented}\n    )"

    chunks = [bodies[i:i + CHUNK] for i in range(0, len(bodies), CHUNK)]

    if len(chunks) == 1:
        union_block = "| union\n" + ",\n".join(branch(b) for b in chunks[0])
    else:
        outer_branches = []
        for ch in chunks:
            inner = ",\n".join(branch(b) for b in ch)
            # Re-indent inner by 2 spaces because it's wrapped inside an outer (
            inner_re = "\n".join(("  " + ln) if ln.strip() else ln for ln in inner.split("\n"))
            outer_branches.append(f"(\n  | union\n{inner_re}\n)")
        union_block = "| union\n" + ",\n".join(outer_branches)

    header = (
        "// 12_distinct_count_features.pq\n"
        "// Hourly distinct-count features. Each branch is a full self-contained\n"
        "// pipeline using the verified 2-stage `group(inner) | group(outer)` pattern\n"
        "// (dcount on parsed fields 500s when combined with timebucket). Branches\n"
        "// are unioned (max 10 per union, nested for >10). Each branch already\n"
        "// emits the final schema (entity_type, entity_id, hour_ts, family,\n"
        "// feature_name, value), so the merged stream is written directly.\n"
        "//\n"
    )

    out = header + union_block + "\n| savelookup 'ueba_features_hourly', 'merge'\n"
    open(PATH, "w").write(out)
    print(f"  wrote {len(out.splitlines())} lines to {PATH}")

if __name__ == "__main__":
    main()
