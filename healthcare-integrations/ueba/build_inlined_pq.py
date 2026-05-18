#!/usr/bin/env python3
"""
Build inlined runnable .pq files from the source .pq files.

For files that use `let base = (...) ; | union (base | columns ...) ...`
we expand the `let` and then EMIT ONE FILE PER UNION BRANCH so each
output file stays under the 15,000-character /api/powerQuery limit.

For single-query files (06-11) we copy verbatim.

Output layout:
    inlined-pq/
        01_features_auth/                  <- one dir per multi-branch source
            01_auth_total.pq
            01_auth_fail.pq
            ...
        02_features_endpoint/
            ...
        06_peers_dynamic.pq                <- single-query files stay flat
        07_baselines_entity.pq
        ...
        README.md
"""
from __future__ import annotations
import re, shutil, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT  = HERE / "inlined-pq"
ZIP  = HERE / "ueba-healthcare-inlined-pq.zip"

SOURCES = [
    "01_features_auth.pq",
    "02_features_endpoint.pq",
    "03_features_network.pq",
    "04_features_cloud.pq",
    "05_features_healthcare.pq",
    "06_peers_dynamic.pq",
    "07_baselines_entity.pq",
    "08_baselines_peer.pq",
    "09_scoring.pq",
    "09b_family_scores.pq",
    "10_risk_daily.pq",
    "11_alerts.pq",
    "12_distinct_count_features.pq",
]


def strip_comments(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines()
                     if not ln.lstrip().startswith("//")).strip()


def extract_let_base(text: str):
    """Find a single top-level `let <name> = ( <body> );` and return
    (name, body, remainder_text). Returns (None, None, text) if none."""
    m = re.search(
        r'^\s*let\s+(\w+)\s*=\s*\(\s*\n?(.*?)\n?\s*\)\s*;\s*\n',
        text, re.S | re.M,
    )
    if not m:
        return None, None, text
    return m.group(1), m.group(2).strip(), text[m.end():]


def extract_union_branches(text: str):
    """Given the post-`let` remainder, return (branches, tail) where:
       branches = list of branch body strings (the `<expr>` from each
                  `( <expr> )` in the `| union ( ... ), ( ... ), ... | tail`)
       tail     = everything from `|` after the last `)` to end-of-file.
    """
    # Strip the leading `| union` token
    s = re.sub(r'^\s*\|\s*union\b', '', text.strip())
    # Walk balanced parens at top level
    branches = []
    depth = 0
    cur = []
    i = 0
    last_close = -1
    while i < len(s):
        ch = s[i]
        if ch == '(':
            if depth == 0:
                cur = []
            else:
                cur.append(ch)
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                branches.append("".join(cur).strip())
                last_close = i
            else:
                cur.append(ch)
        elif depth > 0:
            cur.append(ch)
        i += 1
    tail = s[last_close + 1:].lstrip(", \t\r\n")
    return branches, tail


def feature_name_of(branch: str) -> str:
    """Pull the feature_name = "..." literal out of a branch's `| columns`
    clause, for naming the output file. Fallback to a hash."""
    m = re.search(r'feature_name\s*=\s*"([^"]+)"', branch)
    if m:
        return m.group(1)
    m = re.search(r'feature_name\s*=\s*\'([^\']+)\'', branch)
    if m:
        return m.group(1)
    return f"branch_{hash(branch) & 0xffff:04x}"


def build_branch_query(name_body: str, branch_columns: str, tail: str) -> str:
    """Assemble:   <base body>
                   | <columns ...>
                   | <tail commands>
    Note the branch body starts with `<name> | columns ...` so we strip
    leading `<name>` and substitute the base body in its place."""
    # name_body is the inlined base pipeline (no `<name>` token)
    # branch_columns is the rest of the branch: `<name> | columns ...`
    # Strip the leading name token from branch_columns
    bc = re.sub(r'^\s*\w+\s*\|\s*', '| ', branch_columns)
    return f"{name_body}\n{bc}\n{tail}".strip()


def split_inlined_union(text: str):
    """Handle the already-inlined form:
       `| union ( <branch1> ), ( <branch2> ), ... | <tail>`.
       Returns (branches, tail).
       For nested unions, recursively flattens to leaf branches."""
    branches, tail = extract_union_branches(text)
    # Recursively expand inner unions
    leaves = []
    for b in branches:
        if re.search(r'^\s*\|\s*union\b', b):
            inner, _ = extract_union_branches(b)
            leaves.extend(inner)
        else:
            leaves.append(b)
    return leaves, tail


def emit_multi_branch(src_path: Path, out_dir: Path) -> int:
    """Split a source into N independent per-branch .pq files. Handles:
       (1) `let base = (...) ; | union (base | columns ...) ... | tail`
       (2) Already-inlined  `| union ( <full pipeline> ), ... | tail`"""
    text = src_path.read_text()
    clean = strip_comments(text)
    name, body, remainder = extract_let_base(clean)
    written = 0
    prefix = src_path.stem.split("_", 1)[0]  # "01", "02", ...

    if name:
        # Form 1: explicit let base. Inline base into each branch.
        branches, tail = extract_union_branches(remainder)
        queries = [build_branch_query(body, b, tail) for b in branches]
        feat_names = [feature_name_of(b) for b in branches]
    else:
        # Form 2: already inlined.
        leaves, tail = split_inlined_union(clean)
        queries = [f"{b.strip()}\n{tail}".strip() for b in leaves]
        feat_names = [feature_name_of(b) for b in leaves]

    for q, fname in zip(queries, feat_names):
        out_path = out_dir / f"{prefix}_{fname}.pq"
        out_path.write_text(
            f"// Auto-generated from {src_path.name}\n"
            f"// Feature: {fname}\n"
            f"// Writes to: ueba_features_hourly\n\n"
            + q + "\n"
        )
        written += 1
    return written


def collapse_blanks(text: str) -> str:
    return re.sub(r'\n\s*\n\s*\n+', '\n\n', text)


README_BODY = """# UEBA Healthcare — Runnable PowerQuery files

Inlined, self-contained PowerQuery (.pq) files derived from
https://github.com/marcredhat/ueba-healthcare. Every `let X = ( ... )`
definition has been pasted inline because the SDL parser on the target
tenant rejects `let X = (subquery)` aliasing.

For files that produced more than one feature via a single `| union`
(01–05, 12), the source has been **split into one .pq per feature** so
that each file stays under the 15,000-character `/api/powerQuery`
request-body limit.

## Layout

```
01_features_auth/
    01_auth_total.pq
    01_auth_fail.pq
    ...
02_features_endpoint/
    ...
06_peers_dynamic.pq           # single-query files stay flat
07_baselines_entity.pq
08_baselines_peer.pq
09_scoring.pq
09b_family_scores.pq
10_risk_daily.pq
11_alerts.pq
```

## Running one file

```bash
QUERY=$(cat 01_features_auth/01_auth_total.pq)
curl -X POST "$SDL_URL/api/powerQuery"                  \\
     -H "Authorization: Bearer $SDL_LOG_READ_KEY"        \\
     -H "Content-Type: application/json"                 \\
     -d "{\\"query\\":\\"$QUERY\\",\\"startTime\\":\\"24h\\"}"
```

Or paste any file into the AI SIEM PowerQuery UI.

## Pipeline order

1. 01–05, 12 (features → `ueba_features_hourly`)
2. 06 (peers → `ueba_peer_membership`)
3. 07 (entity baselines → `ueba_baselines_entity`)
4. 08 (peer baselines → `ueba_baselines_peer`)
5. 09 (scoring → `ueba_feature_scores_hourly`)
6. 09b (family rollup → `ueba_family_scores_hourly`)
7. 10 (daily risk → `ueba_entity_risk`)
8. 11 (alerts → `ueba_alerts`)
"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    counts = {}
    for name in SOURCES:
        p = HERE / name
        if not p.exists():
            print(f"  MISSING  {name}")
            continue
        clean = strip_comments(p.read_text())
        # Multi-branch if either uses `let base = (...)` or starts with `| union`
        has_union = bool(re.search(r'^\s*\|\s*union\b', clean, re.M))
        is_multi  = has_union and ("| columns" in clean) and (
            "let " in clean or clean.count("(") >= 4
        )
        if is_multi:
            sub = OUT / p.stem
            sub.mkdir(exist_ok=True)
            n = emit_multi_branch(p, sub)
            counts[name] = n
            print(f"  [SPLIT]  {name:<35}  -> {n} per-feature .pq files")
        else:
            (OUT / p.name).write_text(p.read_text())
            counts[name] = 1
            print(f"  [COPY ]  {name:<35}  -> 1 .pq file")

    (OUT / "README.md").write_text(README_BODY)

    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                arc = "ueba-healthcare-inlined-pq/" + str(p.relative_to(OUT))
                zf.write(p, arcname=arc)

    total = sum(counts.values())
    print(f"\nTOTAL: {total} runnable .pq files")
    print(f"Zip  : {ZIP}  ({ZIP.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
