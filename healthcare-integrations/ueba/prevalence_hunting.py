#!/usr/bin/env python3
"""
Prevalence & contextual hunting — PowerQuery patterns to measure how
widespread a specific activity is across hosts / sites / users, and
distinguish isolated behaviour from campaign-like spread.

This script defines five canonical hunt queries, runs each against the
tenant, and prints results so each pattern is verified end-to-end.

Target activity = "VPN_TUNNEL_FAILED on a TI Konnektor", chosen because
the tenant has rich Avelios + Omniconnect data and the same pattern
applies to any activity (just swap the filter line at the top).
"""
from __future__ import annotations
import os, sys, requests, urllib3
from pathlib import Path

urllib3.disable_warnings()

HERE = Path(__file__).resolve().parent
SDL = Path(os.environ.get(
    "SDL_API_DIR",
    str(HERE.parent.parent / "sentinelone-sdl-api"),
))
sys.path.insert(0, str(SDL / "scripts"))
import sdl_client  # noqa: E402
sdl_client.CONFIG_PATH = SDL / "config.json"
from sdl_client import SDLClient  # noqa: E402


c = SDLClient()
URL = f"{c.base_url}/api/powerQuery"
H   = c._build_headers("log_read")


def run(label: str, q: str, start: str = "48h") -> None:
    r = requests.post(URL, headers=H,
        json={"query": q, "startTime": start, "priority": "low"},
        timeout=180, verify=c.verify_tls)
    print("\n" + "=" * 78)
    print(f"  {label}    [start={start}]")
    print("=" * 78)
    if not r.ok:
        print(f"FAIL HTTP{r.status_code}\n{r.text[:400]}")
        return
    j = r.json()
    cols = [x["name"] for x in (j.get("columns") or [])]
    rows = j.get("values") or []
    print(f"rows={len(rows)}  cols={cols}\n")
    widths = [max(len(str(c)), 8) for c in cols]
    for ri, row in enumerate(rows[:25]):
        widths = [max(w, len(str(v))) for w, v in zip(widths, row)]
    fmt = "  ".join("{:<" + str(w) + "}" for w in widths)
    print(fmt.format(*cols))
    print(fmt.format(*["-" * w for w in widths]))
    for row in rows[:25]:
        print(fmt.format(*[str(v)[:60] for v in row]))


# ---------------------------------------------------------------------------
# Define the "activity of interest" once.  Change just this filter to retarget
# the entire workflow at any other event.
# ---------------------------------------------------------------------------
TARGET_FILTER = """\
| parse '"event_type": "$event_type{regex=[^"]+}$"' from message
| parse '"event_category": "$event_cat{regex=[^"]+}$"' from message
| parse '"hostname": "$host{regex=[^"]+}$"'             from message
| parse '"username": "$username{regex=[^"]+}$"'         from message
| parse '"hospital_name": "$hospital_name{regex=[^"]+}$"' from message
| parse '"bsnr": "$bsnr{regex=[^"]+}$", "name": "$facility_name{regex=[^"]+}$"' from message
| parse '"location": "$city{regex=[^"]+}$"'             from message
| parse '"type": "$facility_type{regex=[^"]+}$"'        from message
| parse '"telematik_id": "$telematik_id{regex=[^"]+}$"' from message
| parse '"outcome": "$outcome{regex=[^"]+}$"'           from message
| parse '"severity": "$sev{regex=[^"]+}$"'              from message
// Unify site = either Avelios hospital_name or Omniconnect facility.name
| let site = hospital_name = null ? facility_name : hospital_name
// Use host as fallback identity when the activity has no user context
| let who = username = null ? host : username
| filter event_type = "VPN_TUNNEL_FAILED"
"""


# ---------------------------------------------------------------------------
# Q1 — Raw prevalence: how many events, how many distinct dimensions?
# ---------------------------------------------------------------------------
Q1 = TARGET_FILTER + """
| group total_events = count(),
        distinct_hosts    = estimate_distinct(host),
        distinct_users    = estimate_distinct(username),
        distinct_sites    = estimate_distinct(site),
        distinct_cities   = estimate_distinct(city),
        distinct_facility_types = estimate_distinct(facility_type),
        first_seen_ns = min(timestamp),
        last_seen_ns  = max(timestamp)
| let span_min = (last_seen_ns - first_seen_ns) / (60.0 * 1000000000)
| columns total_events, distinct_hosts, distinct_users, distinct_sites,
          distinct_cities, distinct_facility_types, span_min
"""


# ---------------------------------------------------------------------------
# Q2 — Prevalence by HOST (asset group equivalent)
# ---------------------------------------------------------------------------
Q2 = TARGET_FILTER + """
| group n = count(),
        first_ns = min(timestamp),
        last_ns  = max(timestamp),
        distinct_users = estimate_distinct(username),
        distinct_sites = estimate_distinct(site)
    by host, facility_type
| filter host = *
| let active_min = (last_ns - first_ns) / (60.0 * 1000000000)
| sort -n
| columns host, facility_type, n, distinct_users, distinct_sites, active_min
| limit 25
"""


# ---------------------------------------------------------------------------
# Q3 — Prevalence by SITE (hospital / pharmacy / practice)
# ---------------------------------------------------------------------------
Q3 = TARGET_FILTER + """
| group n = count(),
        distinct_hosts = estimate_distinct(host),
        distinct_users = estimate_distinct(username),
        distinct_telematik = estimate_distinct(telematik_id)
    by site, city, facility_type
| filter site = *
| sort -n
| columns site, city, facility_type, n, distinct_hosts, distinct_users, distinct_telematik
| limit 25
"""


# ---------------------------------------------------------------------------
# Q4 — Prevalence by USER ACCOUNT
# ---------------------------------------------------------------------------
Q4 = TARGET_FILTER + """
| group n = count(),
        distinct_hosts = estimate_distinct(host),
        distinct_sites = estimate_distinct(site),
        first_ns = min(timestamp),
        last_ns  = max(timestamp)
    by who
| filter who = *
| let span_min = (last_ns - first_ns) / (60.0 * 1000000000)
| sort -n
| columns who, n, distinct_hosts, distinct_sites, span_min
| limit 25
"""


# ---------------------------------------------------------------------------
# Q5 — Campaign classifier:
#       bucket the activity per hour, then characterise spread vs concentration.
#       The (hosts × sites)/events ratio separates campaign (high) from isolated (low).
# ---------------------------------------------------------------------------
Q5 = TARGET_FILTER + """
| group n = count(),
        distinct_hosts = estimate_distinct(host),
        distinct_sites = estimate_distinct(site),
        distinct_users = estimate_distinct(username)
    by bucket_1h = timebucket('1 hour')
| let spread_score = (1.0 * distinct_hosts * distinct_sites) / n
| let classification =
        distinct_sites >= 3 AND distinct_hosts >= 5 ? "CAMPAIGN"
      : distinct_sites >= 2                          ? "WIDESPREAD"
      : distinct_hosts >= 3                          ? "LOCALIZED"
                                                     : "ISOLATED"
| sort -bucket_1h
| columns bucket_1h, n, distinct_hosts, distinct_sites, distinct_users,
          spread_score, classification
| limit 48
"""


def main() -> int:
    print(f"Tenant : {c.base_url}")
    print(f"Target : VPN_TUNNEL_FAILED on TI Konnektors (48h window)")

    run("Q1  Headline prevalence (single-row summary)", Q1)
    run("Q2  Prevalence by HOST (asset-group view)",    Q2)
    run("Q3  Prevalence by SITE (hospital/pharmacy)",   Q3)
    run("Q4  Prevalence by USER ACCOUNT",               Q4)
    run("Q5  Campaign classifier (per-hour spread)",    Q5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
