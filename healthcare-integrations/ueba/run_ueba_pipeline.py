#!/usr/bin/env python3
"""
End-to-end UEBA pipeline orchestrator (replaces files 06, 09, 10, 11).

Why Python instead of SDL native:
  * SDL PowerQuery on this tenant has no string-concat function, `||` is
    boolean-only, savelookup overwrites, and let-as-subquery-alias is rejected.
  * Multi-step pipelines with joins across datatables work, but the syntax is
    fragile and tenant-specific. Python is more reliable for the orchestration
    layer.

Stages:
  1. peers   — derive USER (role, hospital) + HOST (hostname, location) peers
               from raw auth events, write /datatables/ueba_peer_membership
  2. baselines — for each (entity, feature_name), compute rolling mean/std/q99
                 over the last 14 days, write /datatables/ueba_baselines_entity
  3. peer_baselines — same over peer groups, write /datatables/ueba_baselines_peer
  4. scoring — z-score self + peer + quantile breaches per feature, family-level
               percentile, write /datatables/ueba_family_scores_hourly
  5. risk    — daily entity risk with exponential decay (half-life 48h),
               write /datatables/ueba_entity_risk
  6. alerts  — family_score > 90 (hourly) or daily_risk > 70, write
               /datatables/ueba_alerts

Inputs: /datatables/ueba_features_hourly (produced by run_pq_combined.py --all)

Usage:
    python3 run_ueba_pipeline.py                 # all stages
    python3 run_ueba_pipeline.py --stage peers   # one stage
    python3 run_ueba_pipeline.py --dry           # don't write to SDL
"""
import argparse
import json
import math
import re
import sys
import time
from collections import defaultdict
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

# Tunables
BASELINE_WINDOW_DAYS = 14
FAMILY_PERCENTILE = 95     # family score = p95 of feature_scores
FAMILY_SCORE_SCALE = 10    # multiply by 10 then cap at 100
HALF_LIFE_HOURS = 48       # risk decay
FAMILY_WEIGHTS = {
    "auth":     1.0,
    "endpoint": 1.3,
    "network":  0.8,
    "cloud":    1.4,
    "healthcare": 1.5,
    "web":      0.6,
    "dns":      0.7,
    "file":     0.9,
}
ALERT_FAMILY_THRESHOLD = 90
ALERT_RISK_THRESHOLD = 70


def pq(client: SDLClient, query: str, start: str = "14d") -> dict:
    r = requests.post(
        f"{client.base_url}/api/powerQuery",
        headers=client._build_headers("log_read"),
        json={"query": query, "startTime": start, "priority": "low"},
        timeout=120, verify=client.verify_tls,
    )
    if not r.ok:
        return {"_http": r.status_code, "_text": r.text}
    return r.json()


def put_datatable(client: SDLClient, table: str, columns: list, rows: list) -> dict:
    path = f"/datatables/{table}"
    content = json.dumps({"columnNames": columns, "rows": rows}, default=str)
    body = {"path": path, "content": content}
    try:
        g = requests.post(
            f"{client.base_url}/api/getFile",
            headers=client._build_headers("config_read"),
            json={"path": path}, timeout=30, verify=client.verify_tls,
        )
        if g.ok and "version" in g.json():
            body["expectedVersion"] = g.json()["version"]
    except Exception:
        pass
    r = requests.post(
        f"{client.base_url}/api/putFile",
        headers=client._build_headers("config_write"),
        json=body, timeout=120, verify=client.verify_tls,
    )
    if not r.ok:
        return {"_http": r.status_code, "_text": r.text[:400]}
    return r.json()


def fetch_table(client: SDLClient, table: str, extra: str = "") -> tuple:
    """Fetch a config datatable, return (columns, rows).

    Default PowerQuery response is capped at 1000 rows; we read the raw JSON
    file via /api/getFile to bypass that limit for config datatables.
    """
    path = f"/datatables/{table}"
    try:
        r = requests.post(
            f"{client.base_url}/api/getFile",
            headers=client._build_headers("config_read"),
            json={"path": path}, timeout=60, verify=client.verify_tls,
        )
        if r.ok:
            content = r.json().get("content")
            if content:
                d = json.loads(content)
                cols = d.get("columnNames") or []
                rows = d.get("rows") or []
                return cols, rows
        # If file doesn't exist or non-200, fall through to PQ read.
    except Exception:
        pass
    q = f"| dataset 'config://datatables/{table}'"
    if extra:
        q += f" {extra}"
    resp = pq(client, q)
    if "_http" in resp:
        return [], []
    cols = [c["name"] for c in (resp.get("columns") or [])]
    return cols, (resp.get("values") or [])


# ---------- stage 1: peers ----------
def stage_peers(client: SDLClient, dry: bool) -> dict:
    """Derive user peers (role+hospital) and host peers (hostname+location)."""
    print("\n=== stage 1: peers ===")
    user_q = (
        "class_uid = 3002 || class_uid = 4001 "
        '| parse \'"username": "$entity_id{regex=[^"]+}$"\' from message '
        '| parse \'"role": "$role{regex=[^"]+}$"\' from message '
        '| parse \'"hospital_id": "$hospital{regex=[^"]+}$"\' from message '
        "| group n = count() by entity_id, role, hospital "
        "| filter entity_id = * "
        "| filter role = * "
        "| filter hospital = * "
        "| columns entity_id, role, hospital"
    )
    resp = pq(client, user_q, start="7d")
    user_rows = resp.get("values") or [] if "_http" not in resp else []
    print(f"  raw user-role-hospital rows: {len(user_rows)}")

    host_q = (
        "class_uid = 3002 || class_uid = 4001 "
        '| parse \'"hostname": "$entity_id{regex=[^"]+}$"\' from message '
        '| parse \'"location": "$loc{regex=[^"]+}$"\' from message '
        "| group n = count() by entity_id, loc "
        "| filter entity_id = * "
        "| columns entity_id, loc"
    )
    resp = pq(client, host_q, start="7d")
    host_rows = resp.get("values") or [] if "_http" not in resp else []
    print(f"  raw host-location rows: {len(host_rows)}")

    out = []
    for entity_id, role, hospital in user_rows:
        peer_id = f"role={role}|hosp={hospital}"
        out.append(["user", entity_id, peer_id])
    for entity_id, loc in host_rows:
        # host family from first hyphen-separated token
        fam = (entity_id or "").split("-")[0] or "unknown"
        peer_id = f"host_fam={fam}|loc={loc or 'unknown'}"
        out.append(["host", entity_id, peer_id])

    print(f"  peer-membership rows: {len(out)}")
    if dry:
        print(f"  (dry) sample: {out[:3]}")
        return {"rows": len(out)}
    r = put_datatable(client, "ueba_peer_membership",
                      ["entity_type", "entity_id", "peer_id"], out)
    print(f"  put: {json.dumps(r)[:200]}")
    return {"rows": len(out)}


# ---------- stage 2: entity baselines ----------
def _stats(values: list) -> tuple:
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0
    mu = sum(values) / n
    var = sum((v - mu) ** 2 for v in values) / n
    sigma = math.sqrt(var)
    s = sorted(values)
    q99 = s[min(int(0.99 * n), n - 1)]
    return mu, sigma, q99


def stage_baselines(client: SDLClient, dry: bool) -> dict:
    """For each (entity_type, entity_id, feature_name) compute mu, sigma, q99
    from the last BASELINE_WINDOW_DAYS days of ueba_features_hourly."""
    print("\n=== stage 2: entity baselines ===")
    cols, rows = fetch_table(client, "ueba_features_hourly")
    print(f"  features_hourly rows: {len(rows)}")
    if not rows:
        return {"rows": 0}
    # columns: entity_type, entity_id, hour_ts, family, feature_name, value
    idx = {c: i for i, c in enumerate(cols)}
    series = defaultdict(list)
    for r in rows:
        key = (r[idx["entity_type"]], r[idx["entity_id"]],
               r[idx["family"]], r[idx["feature_name"]])
        try:
            v = float(r[idx["value"]])
        except (TypeError, ValueError):
            continue
        series[key].append(v)

    out = []
    for (etype, eid, fam, feat), vals in series.items():
        mu, sigma, q99 = _stats(vals)
        out.append([etype, eid, fam, feat, mu, sigma, q99, len(vals)])
    print(f"  baseline rows: {len(out)}")
    if dry:
        print(f"  (dry) sample: {out[:2]}")
        return {"rows": len(out)}
    r = put_datatable(client, "ueba_baselines_entity",
                      ["entity_type", "entity_id", "family", "feature_name",
                       "mu", "sigma", "q99", "n"], out)
    print(f"  put: {json.dumps(r)[:200]}")
    return {"rows": len(out)}


# ---------- stage 3: peer baselines ----------
def stage_peer_baselines(client: SDLClient, dry: bool) -> dict:
    print("\n=== stage 3: peer baselines ===")
    fc, frows = fetch_table(client, "ueba_features_hourly")
    pc, prows = fetch_table(client, "ueba_peer_membership")
    if not frows or not prows:
        print(f"  features={len(frows)} peers={len(prows)} -> skip")
        return {"rows": 0}
    fi = {c: i for i, c in enumerate(fc)}
    pi = {c: i for i, c in enumerate(pc)}
    # map (entity_type, entity_id) -> peer_id
    peer_of = {}
    for r in prows:
        peer_of[(r[pi["entity_type"]], r[pi["entity_id"]])] = r[pi["peer_id"]]

    series = defaultdict(list)
    for r in frows:
        et, eid = r[fi["entity_type"]], r[fi["entity_id"]]
        peer_id = peer_of.get((et, eid))
        if not peer_id:
            continue
        try:
            v = float(r[fi["value"]])
        except (TypeError, ValueError):
            continue
        key = (et, peer_id, r[fi["family"]], r[fi["feature_name"]])
        series[key].append(v)

    out = []
    for (etype, peer_id, fam, feat), vals in series.items():
        mu, sigma, q99 = _stats(vals)
        out.append([etype, peer_id, fam, feat, mu, sigma, q99, len(vals)])
    print(f"  peer-baseline rows: {len(out)}")
    if dry:
        return {"rows": len(out)}
    r = put_datatable(client, "ueba_baselines_peer",
                      ["entity_type", "peer_id", "family", "feature_name",
                       "mu", "sigma", "q99", "n"], out)
    print(f"  put: {json.dumps(r)[:200]}")
    return {"rows": len(out)}


# ---------- stage 4: scoring ----------
def stage_scoring(client: SDLClient, dry: bool) -> dict:
    """For each (entity, hour, feature), compute feature_score; aggregate to
    family_score at the (entity, hour, family) level."""
    print("\n=== stage 4: scoring (family_scores_hourly) ===")
    fc, frows = fetch_table(client, "ueba_features_hourly")
    bc, brows = fetch_table(client, "ueba_baselines_entity")
    pmc, pmrows = fetch_table(client, "ueba_peer_membership")
    pbc, pbrows = fetch_table(client, "ueba_baselines_peer")
    if not frows or not brows:
        print(f"  features={len(frows)} baselines={len(brows)} -> skip")
        return {"rows": 0}
    fi = {c: i for i, c in enumerate(fc)}
    bi = {c: i for i, c in enumerate(bc)}
    pmi = {c: i for i, c in enumerate(pmc)} if pmc else {}
    pbi = {c: i for i, c in enumerate(pbc)} if pbc else {}

    base_e = {}
    for r in brows:
        base_e[(r[bi["entity_type"]], r[bi["entity_id"]],
                r[bi["feature_name"]])] = (
            float(r[bi["mu"]] or 0), float(r[bi["sigma"]] or 0),
            float(r[bi["q99"]] or -1))
    peer_of = {}
    for r in pmrows:
        peer_of[(r[pmi["entity_type"]], r[pmi["entity_id"]])] = r[pmi["peer_id"]]
    base_p = {}
    for r in pbrows:
        base_p[(r[pbi["entity_type"]], r[pbi["peer_id"]],
                r[pbi["feature_name"]])] = (
            float(r[pbi["mu"]] or 0), float(r[pbi["sigma"]] or 0),
            float(r[pbi["q99"]] or -1))

    # feature_score per (entity, hour, family, feature)
    rows_scored = []
    family_buckets = defaultdict(list)
    for r in frows:
        et, eid = r[fi["entity_type"]], r[fi["entity_id"]]
        hr = r[fi["hour_ts"]]
        fam = r[fi["family"]]
        feat = r[fi["feature_name"]]
        try:
            v = float(r[fi["value"]])
        except (TypeError, ValueError):
            continue

        mu, sigma, q99 = base_e.get((et, eid, feat), (0.0, 0.0, -1.0))
        z_self = ((v - mu) / sigma) if sigma > 0 else 0.0
        over_q99 = 1.0 if (q99 >= 0 and v > q99) else 0.0

        peer_id = peer_of.get((et, eid))
        z_peer = 0.0; over_q99_p = 0.0
        if peer_id:
            mu_p, sigma_p, q99_p = base_p.get((et, peer_id, feat), (0.0, 0.0, -1.0))
            z_peer = ((v - mu_p) / sigma_p) if sigma_p > 0 else 0.0
            over_q99_p = 1.0 if (q99_p >= 0 and v > q99_p) else 0.0

        fscore = max(abs(z_self), abs(z_peer)) + 1.5 * over_q99 + 1.5 * over_q99_p
        rows_scored.append([et, eid, hr, fam, feat, v, round(z_self, 3),
                            round(z_peer, 3), int(over_q99), int(over_q99_p),
                            round(fscore, 3)])
        family_buckets[(et, eid, hr, fam)].append(fscore)

    # family score = p95 of feature_scores, then * 10 capped at 100
    fam_rows = []
    for (et, eid, hr, fam), scores in family_buckets.items():
        s = sorted(scores)
        n = len(s)
        p = s[min(int(0.95 * n), n - 1)] if n > 0 else 0.0
        family_score = min(100.0, p * FAMILY_SCORE_SCALE)
        fam_rows.append([et, eid, hr, fam, round(family_score, 2), n])

    print(f"  feature-level scored rows: {len(rows_scored)}")
    print(f"  family-score rows: {len(fam_rows)}")
    if dry:
        return {"rows": len(fam_rows)}
    r1 = put_datatable(client, "ueba_feature_scores_hourly",
                       ["entity_type", "entity_id", "hour_ts", "family",
                        "feature_name", "value", "z_self", "z_peer",
                        "over_q99", "over_q99_peer", "feature_score"],
                       rows_scored)
    r2 = put_datatable(client, "ueba_family_scores_hourly",
                       ["entity_type", "entity_id", "hour_ts", "family",
                        "family_score", "n_features"],
                       fam_rows)
    print(f"  put feature: {json.dumps(r1)[:120]}")
    print(f"  put family : {json.dumps(r2)[:120]}")
    return {"rows": len(fam_rows)}


# ---------- stage 5: risk ----------
def stage_risk(client: SDLClient, dry: bool) -> dict:
    """Daily entity risk: sum_family(weight * p95_family_score), with decay."""
    print("\n=== stage 5: daily risk ===")
    cols, rows = fetch_table(client, "ueba_family_scores_hourly")
    if not rows:
        print("  no family scores -> skip")
        return {"rows": 0}
    idx = {c: i for i, c in enumerate(cols)}
    # group by (entity_type, entity_id, family, date) -> p95 family_score
    # hour_ts is nanoseconds; convert to date (ns -> sec -> day index)
    NS_PER_DAY = 86_400_000_000_000
    daily = defaultdict(list)
    for r in rows:
        try:
            hr = int(r[idx["hour_ts"]])
            fs = float(r[idx["family_score"]])
        except (TypeError, ValueError):
            continue
        day = hr // NS_PER_DAY
        daily[(r[idx["entity_type"]], r[idx["entity_id"]],
               r[idx["family"]], day)].append(fs)
    fam_daily = {}
    for k, scores in daily.items():
        s = sorted(scores)
        n = len(s)
        fam_daily[k] = s[min(int(0.95 * n), n - 1)] if n else 0.0

    # entity x day -> sum of weighted family daily
    entity_day = defaultdict(float)
    for (et, eid, fam, day), v in fam_daily.items():
        w = FAMILY_WEIGHTS.get(fam, 1.0)
        entity_day[(et, eid, day)] += w * v

    # apply exponential decay across days
    LAMBDA = math.log(2) / HALF_LIFE_HOURS
    by_entity = defaultdict(dict)
    for (et, eid, day), s in entity_day.items():
        by_entity[(et, eid)][day] = s

    out = []
    for (et, eid), days in by_entity.items():
        prev = 0.0
        for day in sorted(days):
            today = days[day]
            decayed = prev * math.exp(-LAMBDA * 24.0)
            score = max(today, decayed)
            out.append([et, eid, day * NS_PER_DAY, round(score, 2)])
            prev = score
    print(f"  daily-risk rows: {len(out)}")
    if dry:
        return {"rows": len(out)}
    r = put_datatable(client, "ueba_entity_risk",
                      ["entity_type", "entity_id", "date", "score"], out)
    print(f"  put: {json.dumps(r)[:200]}")
    return {"rows": len(out)}


# ---------- stage 6: alerts ----------
def stage_alerts(client: SDLClient, dry: bool) -> dict:
    print("\n=== stage 6: alerts ===")
    fc, frows = fetch_table(client, "ueba_family_scores_hourly")
    rc, rrows = fetch_table(client, "ueba_entity_risk")
    alerts = []
    now_ns = int(time.time() * 1_000_000_000)
    if frows:
        fi = {c: i for i, c in enumerate(fc)}
        for r in frows:
            try:
                fs = float(r[fi["family_score"]])
            except (TypeError, ValueError):
                continue
            if fs <= ALERT_FAMILY_THRESHOLD:
                continue
            severity = "critical" if fs > 98 else "high" if fs > 95 else "medium"
            alert_id = (f"fam-{r[fi['hour_ts']]}-{r[fi['entity_type']]}-"
                        f"{r[fi['entity_id']]}-{r[fi['family']]}")
            alerts.append([alert_id, now_ns, r[fi["entity_type"]],
                           r[fi["entity_id"]], r[fi["family"]], severity, fs,
                           f"family_score={fs} (>{ALERT_FAMILY_THRESHOLD})",
                           "new"])
    if rrows:
        ri = {c: i for i, c in enumerate(rc)}
        for r in rrows:
            try:
                sc = float(r[ri["score"]])
            except (TypeError, ValueError):
                continue
            if sc <= ALERT_RISK_THRESHOLD:
                continue
            severity = "critical" if sc > 90 else "high" if sc > 80 else "medium"
            alert_id = (f"risk-{r[ri['date']]}-{r[ri['entity_type']]}-"
                        f"{r[ri['entity_id']]}")
            alerts.append([alert_id, now_ns, r[ri["entity_type"]],
                           r[ri["entity_id"]], "risk", severity, sc,
                           f"daily_risk={sc} (>{ALERT_RISK_THRESHOLD})", "new"])

    print(f"  alerts generated: {len(alerts)}")
    if dry:
        print(f"  (dry) sample: {alerts[:3]}")
        return {"rows": len(alerts)}
    if alerts:
        r = put_datatable(client, "ueba_alerts",
                          ["alert_id", "created_at", "entity_type", "entity_id",
                           "family", "severity", "score", "explanation", "status"],
                          alerts)
        print(f"  put: {json.dumps(r)[:200]}")
    return {"rows": len(alerts)}


STAGES = {
    "peers":     stage_peers,
    "baselines": stage_baselines,
    "peer_baselines": stage_peer_baselines,
    "scoring":   stage_scoring,
    "risk":      stage_risk,
    "alerts":    stage_alerts,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=list(STAGES.keys()), help="run a single stage")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    client = SDLClient()
    if args.stage:
        STAGES[args.stage](client, args.dry)
    else:
        for name, fn in STAGES.items():
            fn(client, args.dry)
    print("\n=== done ===")


if __name__ == "__main__":
    main()
