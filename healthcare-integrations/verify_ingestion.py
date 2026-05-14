#!/usr/bin/env python3
"""
Verify Avelios Medical + Omniconnect ingestion in SDL / AI SIEM.

Runs PowerQueries that prove:
  - events are arriving for both serverHosts
  - the OCSF parser populated category_uid / class_uid / severity_id
  - cross-source BSI / NIS2 security findings are queryable
"""
import sys
from pathlib import Path

SDL_API_DIR = Path(__file__).resolve().parent.parent / "sentinelone-sdl-api"
sys.path.insert(0, str(SDL_API_DIR / "scripts"))
import sdl_client  # noqa: E402
sdl_client.CONFIG_PATH = SDL_API_DIR / "config.json"
from sdl_client import SDLClient  # noqa: E402

HOSTS = ["avelios-medical", "omniconnect"]


def section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def run_query(c: SDLClient, q: str, window: str = "1h") -> dict:
    return c.power_query(query=q, start_time=window)


def print_table(r: dict, max_rows: int = 20) -> None:
    cols = [x["name"] for x in (r.get("columns") or [])]
    rows = r.get("values") or []
    if cols:
        print("  " + " | ".join(cols))
        print("  " + "-" * (sum(len(c) for c in cols) + 3 * len(cols)))
    for row in rows[:max_rows]:
        print("  " + " | ".join(str(v) for v in row))
    if len(rows) > max_rows:
        print(f"  ... ({len(rows) - max_rows} more rows)")


def main(window: str = "1h") -> int:
    c = SDLClient()
    print(f"Connected: {c.base_url}   (window: last {window})")

    # 1. Per-source totals + OCSF coverage
    section("1. Event totals per source")
    for host in HOSTS:
        q = f"serverHost='{host}' | group ct=count() by event_category, class_uid, class_name | sort -ct"
        r = run_query(c, q, window)
        print(f"\n>>> {host}   (matchingEvents={r.get('matchingEvents')})")
        print_table(r)

    # 2. Severity distribution
    section("2. Severity distribution per source")
    for host in HOSTS:
        q = f"serverHost='{host}' | group ct=count() by severity_id, severity_str | sort -severity_id"
        r = run_query(c, q, window)
        print(f"\n>>> {host}")
        print_table(r)

    # 3. BSI / NIS2 security findings (OCSF category_uid=2)
    section("3. BSI / NIS2 security findings (OCSF category_uid=2)")
    q = (
        "(serverHost='avelios-medical' or serverHost='omniconnect') category_uid='2' "
        "| group ct=count() by serverHost, event_type, severity_str "
        "| sort -ct"
    )
    r = run_query(c, q, window)
    print(f"matchingEvents={r.get('matchingEvents')}")
    print_table(r)

    # 4. High / Critical severity across both
    section("4. HIGH / CRITICAL events across both platforms")
    q = (
        "(serverHost='avelios-medical' or serverHost='omniconnect') "
        "(severity_str='HIGH' or severity_str='CRITICAL') "
        "| columns timestamp, serverHost, event_category, event_type, severity_str "
        "| sort -timestamp "
        "| limit 15"
    )
    r = run_query(c, q, window)
    print(f"matchingEvents={r.get('matchingEvents')}")
    print_table(r, max_rows=15)

    # 5. TI infrastructure health (Omniconnect specific)
    section("5. Omniconnect TI infrastructure issues")
    q = (
        "serverHost='omniconnect' (event_category='ti_connection' or event_category='security') "
        "outcome!='success' "
        "| group ct=count() by event_type, severity_str "
        "| sort -ct"
    )
    r = run_query(c, q, window)
    print(f"matchingEvents={r.get('matchingEvents')}")
    print_table(r)

    # 6. Avelios patient-data access (PHI / GDPR)
    section("6. Avelios PHI access (GDPR / BSI Art. 32)")
    q = (
        "serverHost='avelios-medical' event_category='patient_access' "
        "| group ct=count() by event_type "
        "| sort -ct"
    )
    r = run_query(c, q, window)
    print(f"matchingEvents={r.get('matchingEvents')}")
    print_table(r)

    section("DONE")
    print(f"\nView these results live in AI SIEM:\n  {c.base_url}/#/search")
    return 0


if __name__ == "__main__":
    win = sys.argv[1] if len(sys.argv) > 1 else "1h"
    sys.exit(main(win))
