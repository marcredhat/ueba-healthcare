#!/usr/bin/env python3
"""Fetch UEBA alerts and explain WHY each fired by tracing back the
contributing feature scores, baselines, and raw feature values."""
import json
import sys
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

c = SDLClient()


def get_file(path):
    r = requests.post(
        f"{c.base_url}/api/getFile",
        headers=c._build_headers("config_read"),
        json={"path": path}, timeout=60, verify=c.verify_tls,
    )
    if not r.ok:
        return None, None
    d = json.loads(r.json().get("content", "{}"))
    return d.get("columnNames") or [], d.get("rows") or []


def as_dicts(cols, rows):
    return [dict(zip(cols, r)) for r in rows]


# Load all relevant tables
alert_cols, alert_rows = get_file("/datatables/ueba_alerts")
fam_cols, fam_rows = get_file("/datatables/ueba_family_scores_hourly")
feat_cols, feat_rows = get_file("/datatables/ueba_feature_scores_hourly")
base_cols, base_rows = get_file("/datatables/ueba_baselines_entity")
risk_cols, risk_rows = get_file("/datatables/ueba_entity_risk")

alerts = as_dicts(alert_cols, alert_rows)
fam = as_dicts(fam_cols, fam_rows)
feats = as_dicts(feat_cols, feat_rows)
bases = as_dicts(base_cols, base_rows)
risks = as_dicts(risk_cols, risk_rows)

print(f"\n{'='*78}")
print(f"  UEBA ALERT EXPLANATIONS  ({len(alerts)} alerts)")
print(f"{'='*78}")

for a in alerts:
    print(f"\n┌─ alert: {a['alert_id']}")
    print(f"│  severity : {a['severity'].upper()}    score={a['score']:.1f}    status={a['status']}")
    print(f"│  entity   : {a['entity_type']} / {a['entity_id']}")
    print(f"│  family   : {a['family']}")
    print(f"│  trigger  : {a['explanation']}")

    fam_kind = a["family"]   # e.g. "auth", "risk"
    eid = a["entity_id"]
    etype = a["entity_type"]

    if a["alert_id"].startswith("fam-"):
        # Family-level hourly alert — find the contributing feature scores
        # Find matching family_score row
        hour_ts = int(a["alert_id"].split("-")[1])
        matching_fam = [f for f in fam
                        if f["entity_id"] == eid and f["family"] == fam_kind
                        and int(f["hour_ts"]) == hour_ts]
        if matching_fam:
            mf = matching_fam[0]
            print(f"│")
            print(f"│  family_score breakdown for hour {hour_ts}:")
            print(f"│    family_score = {mf['family_score']:.2f}  "
                  f"(p95 of {mf['n_features']} feature_scores × 10, capped at 100)")

        # Find top-contributing feature scores at that hour
        contribs = [f for f in feats
                    if f["entity_id"] == eid and f["family"] == fam_kind
                    and int(f["hour_ts"]) == hour_ts]
        contribs.sort(key=lambda r: -float(r["feature_score"]))
        if contribs:
            print(f"│")
            print(f"│  top contributing features:")
            for cf in contribs[:5]:
                # Look up baseline for context
                base = next((b for b in bases
                             if b["entity_id"] == eid
                             and b["feature_name"] == cf["feature_name"]
                             and b["family"] == fam_kind), None)
                base_str = ""
                if base:
                    mu = float(base.get("mu") or 0)
                    sigma = float(base.get("sigma") or 0)
                    q99 = float(base.get("q99") or 0)
                    n = base.get("n") or 0
                    base_str = (f"  [baseline mu={mu:.2f} σ={sigma:.2f} "
                                f"q99={q99:.2f} n={n}]")
                flags = []
                if int(cf["over_q99"] or 0):
                    flags.append("OVER_Q99")
                if int(cf["over_q99_peer"] or 0):
                    flags.append("OVER_Q99_PEER")
                flag_str = f"  ⚠ {','.join(flags)}" if flags else ""
                print(f"│    • {cf['feature_name']:<28} value={cf['value']:>6}  "
                      f"z_self={float(cf['z_self']):>5.2f}  "
                      f"z_peer={float(cf['z_peer']):>5.2f}  "
                      f"score={float(cf['feature_score']):>5.2f}{flag_str}")
                if base_str:
                    print(f"│       {base_str}")

    elif a["alert_id"].startswith("risk-"):
        # Daily entity-risk alert — show family contributions for the day
        day_ns = int(a["alert_id"].split("-")[1])
        # daily risk row
        rm = [r for r in risks if r["entity_id"] == eid and int(r["date"]) == day_ns]
        if rm:
            print(f"│")
            print(f"│  daily risk score: {float(rm[0]['score']):.2f}")
        # show family scores for that day
        NS_PER_DAY = 86_400_000_000_000
        same_day = [f for f in fam
                    if f["entity_id"] == eid
                    and (int(f["hour_ts"]) // NS_PER_DAY) == (day_ns // NS_PER_DAY)]
        if same_day:
            from collections import defaultdict
            by_fam = defaultdict(list)
            for f in same_day:
                by_fam[f["family"]].append(float(f["family_score"]))
            print(f"│  family contributions on this day:")
            for famname, scores in sorted(by_fam.items(), key=lambda kv: -max(kv[1])):
                scores.sort(reverse=True)
                p95 = scores[min(int(0.95 * len(scores)), len(scores) - 1)]
                print(f"│    • {famname:<12}  n_hours={len(scores):>3}  "
                      f"max={max(scores):>6.2f}  p95={p95:>6.2f}")

    print(f"└─")
