#!/usr/bin/env python3
"""
Mechanically transform feature-extractor .pq files from the
`let base = (subquery); union ( base | columns ... )` form
into the inlined-union form proven by file 01.

Reads each file in FILES, extracts (BASE pipeline, [(feature_name, column)],
trailing entity_type/family line), and emits the new file with each union
branch carrying a full copy of BASE plus its own `| columns` line.
Unions are split into chunks of 10 to stay within the SDL limit.
"""
import os, re, sys

FILES = [
    "02_features_endpoint.pq",
    "03_features_network.pq",
    "04_features_cloud.pq",
    "05_features_healthcare.pq",
]

UNION_CHUNK = 10
HEADER_PREFIX = """// {fname}
// Hourly feature extractor — inlined-union form (file 01 pattern).
// Every union branch repeats the full base pipeline because SDL PowerQuery
// does NOT support `let X = (subquery)` for query aliasing. `union` is also
// capped at 10 subqueries; >10 features use a nested union.
//
"""

def strip_pending_header(src: str) -> str:
    lines = src.split("\n")
    out, skipping = [], False
    i = 0
    while i < len(lines):
        if lines[i].startswith("// PENDING REFACTOR"):
            # skip until next non-comment-block or blank line that isn't a comment
            while i < len(lines) and (lines[i].startswith("//") and "PENDING REFACTOR" in lines[i] or lines[i].startswith("//   ") or lines[i] == "//"):
                i += 1
            continue
        out.append(lines[i]); i += 1
    return "\n".join(out)

def extract(src: str):
    """Return (preamble_comments, base_body, features:[(name,col)], tail)"""
    src = strip_pending_header(src)
    m = re.search(r"^(.*?)let base\s*=\s*\n?\s*\(\s*(.*?)\s*\)\s*;\s*\n+\|?\s*union\s*\n(.*?)\n(\| let entity_type[^\n]*\n\| columns[^\n]*\n\| savelookup[^\n]*)",
                  src, re.S)
    if not m:
        raise SystemExit(f"  could not parse file structure")
    preamble = m.group(1).rstrip() + "\n"
    base_body = m.group(2)
    union_body = m.group(3)
    tail = m.group(4)
    # parse each union branch: ( base | columns entity_id, hour_ts, feature_name = "X", value = Y )
    feats = []
    for fm in re.finditer(
        r"\(\s*base\s*\|\s*columns\s+entity_id,\s*hour_ts,\s*feature_name\s*=\s*\"([^\"]+)\"\s*,\s*value\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)",
        union_body):
        feats.append((fm.group(1), fm.group(2)))
    return preamble, base_body, feats, tail

def emit_branch(base_body: str, fname: str, col: str) -> str:
    # base_body already starts with `| filter ...` etc. (no leading paren).
    # Indent everything two extra spaces and append the columns line.
    indented = "\n".join("      " + line if line.strip() else line for line in base_body.split("\n"))
    return f"""    (
{indented}
      | columns entity_id, hour_ts, feature_name = "{fname}", value = {col}
    )"""

def emit_union(base_body: str, feats: list) -> str:
    """Emit a nested union over feats, chunking by UNION_CHUNK."""
    chunks = [feats[i:i+UNION_CHUNK] for i in range(0, len(feats), UNION_CHUNK)]
    if len(chunks) == 1:
        # Single union, no nesting
        branches = ",\n".join(emit_branch(base_body, n, c) for n, c in chunks[0])
        return f"| union\n{branches}"
    # Nested: outer union of inner unions
    outer = []
    for chunk in chunks:
        inner = ",\n".join(emit_branch(base_body, n, c) for n, c in chunk)
        # the inner branches were indented with 6 spaces; for nested we want them inside ( | union ... )
        # so re-indent by two more spaces.
        inner_indented = "\n".join("  " + line if line.strip() else line for line in inner.split("\n"))
        outer.append(f"(\n  | union\n{inner_indented}\n)")
    return "| union\n" + ",\n".join(outer)

def transform(path: str):
    src = open(path).read()
    preamble, base_body, feats, tail = extract(src)
    if not feats:
        raise SystemExit(f"  no features extracted from {path}")
    header = HEADER_PREFIX.format(fname=path)
    union_block = emit_union(base_body, feats)
    out = header + preamble + "\n" + union_block + "\n" + tail + "\n"
    open(path, "w").write(out)
    print(f"  {path}: {len(feats)} features -> {len(out.splitlines())} lines")

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    for f in FILES:
        print(f"transforming {f}...")
        transform(f)

if __name__ == "__main__":
    main()
