#!/usr/bin/env python3
"""
Deploy BSI / NIS2 healthcare compliance dashboards to SentinelOne SDL.

Follows the sentinelone-sdl-dashboard skill:
  - explicit {w,h,x,y} layout on 60-wide grid
  - markdown panels use `markdown` field (not `content`)
  - number panels end in `| limit 1`
  - donut queries: 1 text + 1 numeric column
  - CAS guard via expected_version on put_file
  - verify by re-fetch + canary grep

Two dashboards deployed:
  /dashboards/bsi-nis2-healthcare-overview   (TABBED: Overview / Avelios / Omniconnect / Security)
  /dashboards/bsi-nis2-compliance-controls   (compliance-control-mapping focused)
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SDL_API_DIR = ROOT.parent.parent / "sentinelone-sdl-api"
sys.path.insert(0, str(SDL_API_DIR / "scripts"))
import sdl_client  # noqa: E402
sdl_client.CONFIG_PATH = SDL_API_DIR / "config.json"
from sdl_client import SDLClient  # noqa: E402


# ─── Grid helper from the skill ───────────────────────────────────────────
class Grid:
    def __init__(self, width: int = 60):
        self.W = width
        self.x = 0
        self.y = 0
        self.row_h = 0

    def place(self, w: int, h: int) -> dict:
        if self.x + w > self.W:
            self.y += self.row_h
            self.x = 0
            self.row_h = 0
        layout = {"w": w, "h": h, "x": self.x, "y": self.y}
        self.x += w
        self.row_h = max(self.row_h, h)
        return layout

    def newline(self) -> None:
        if self.x > 0:
            self.y += self.row_h
            self.x = 0
            self.row_h = 0


# ─── Panel factories ──────────────────────────────────────────────────────
def md(title: str, body: str, g: Grid, h: int = 6, w: int = 60) -> dict:
    return {
        "title": title,
        "graphStyle": "markdown",
        "markdown": body,
        "layout": g.place(w, h),
    }


def number(title: str, query: str, g: Grid, suffix: str = "", w: int = 15, h: int = 8) -> dict:
    if "| limit 1" not in query:
        query = query.rstrip() + " | limit 1"
    return {
        "title": title,
        "graphStyle": "number",
        "query": query,
        "options": {"format": "auto", "precision": "0", "suffix": suffix},
        "layout": g.place(w, h),
    }


def donut(title: str, query: str, g: Grid, w: int = 30, h: int = 14, max_slices: int = 10) -> dict:
    return {
        "title": title,
        "graphStyle": "donut",
        "maxPieSlices": max_slices,
        "dataLabelType": "PERCENTAGE",
        "query": query,
        "layout": g.place(w, h),
    }


def table(title: str, query: str, g: Grid, w: int = 30, h: int = 14) -> dict:
    if "| limit" not in query:
        query = query.rstrip() + " | limit 25"
    return {
        "title": title,
        "graphStyle": "table",
        "query": query,
        "layout": g.place(w, h),
    }


def stacked_bar(title: str, query: str, g: Grid, w: int = 30, h: int = 14, x_axis: str = "grouped_data") -> dict:
    return {
        "title": title,
        "graphStyle": "stacked_bar",
        "xAxis": x_axis,
        "yScale": "linear",
        "query": query,
        "layout": g.place(w, h),
    }


def line(title: str, query: str, g: Grid, w: int = 30, h: int = 14) -> dict:
    return {
        "title": title,
        "graphStyle": "line",
        "lineSmoothing": "straightLines",
        "query": query,
        "layout": g.place(w, h),
    }


# ─── Common predicates ────────────────────────────────────────────────────
HC = "(serverHost='avelios-medical' or serverHost='omniconnect')"
AV = "serverHost='avelios-medical'"
OC = "serverHost='omniconnect'"


# ─── Tab 1: Overview ──────────────────────────────────────────────────────
def build_overview_tab() -> list:
    g = Grid()
    panels = []

    panels.append(md(
        "BSI / NIS2 Healthcare Compliance — Overview",
        (
            "**Scope:** Avelios Medical Hospital Information System (HIS) + "
            "Omniconnect HIS↔Telematics Infrastructure (TI) gateway.\n\n"
            "**Frameworks:** BSI-Grundschutz · NIS2 · GDPR · gematik TI.\n\n"
            "All events are OCSF-enriched (v1.3.0) by the deployed parsers "
            "`Avelios-Medical-OCSF` and `Omniconnect-OCSF`."
        ),
        g, h=4, w=60,
    ))
    g.newline()

    # Number row
    panels.append(number("Total Healthcare Events", f"{HC} | group ct=count()", g, suffix=" events", w=15, h=8))
    panels.append(number("Avelios Events",          f"{AV} | group ct=count()", g, suffix="",        w=15, h=8))
    panels.append(number("Omniconnect Events",      f"{OC} | group ct=count()", g, suffix="",        w=15, h=8))
    panels.append(number("Critical Findings",       f"{HC} severity_id='6' | group ct=count()", g, suffix="",      w=15, h=8))
    g.newline()

    panels.append(donut(
        "Events by Source",
        f"{HC} | group ct=count() by serverHost",
        g, w=30, h=14,
    ))
    panels.append(donut(
        "OCSF Severity Distribution",
        f"{HC} severity_str=* | group ct=count() by severity_str",
        g, w=30, h=14,
    ))
    g.newline()

    panels.append(stacked_bar(
        "Events by OCSF Class (per source)",
        f"{HC} class_name=* | group ct=count() by class_name, serverHost | sort -ct",
        g, w=60, h=16, x_axis="grouped_data",
    ))
    g.newline()

    panels.append(table(
        "Recent HIGH / CRITICAL events",
        (
            f"{HC} (severity_str='HIGH' or severity_str='CRITICAL') "
            "| columns timestamp, serverHost, event_category, event_type, severity_str "
            "| sort -timestamp"
        ),
        g, w=60, h=18,
    ))
    return panels


# ─── Tab 2: Avelios Medical (Hospital HIS) ────────────────────────────────
def build_avelios_tab() -> list:
    g = Grid()
    panels = []

    panels.append(md(
        "Avelios Medical — Hospital Information System",
        (
            "Patient-data access (PHI / GDPR Art. 32), authentication, "
            "administrative changes and security findings.\n\n"
            "**Relevant BSI controls:** ORP.4 (Identity Management), "
            "OPS.1.1 (Logging), CON.3 (Data Protection), DER.1 (Detection)."
        ),
        g, h=4, w=60,
    ))
    g.newline()

    panels.append(number("Total Avelios Events",  f"{AV} | group ct=count()", g, suffix="", w=15, h=8))
    panels.append(number("PHI Access Events",     f"{AV} event_category='patient_access' | group ct=count()", g, suffix="", w=15, h=8))
    panels.append(number("Auth Failures",         f"{AV} event_category='authentication' outcome='failure' | group ct=count()", g, suffix="", w=15, h=8))
    panels.append(number("Security Findings",     f"{AV} category_uid='2' | group ct=count()", g, suffix="", w=15, h=8))
    g.newline()

    panels.append(donut(
        "Avelios — Event Categories",
        f"{AV} event_category=* | group ct=count() by event_category",
        g, w=30, h=14,
    ))
    panels.append(donut(
        "Avelios — Severity Mix",
        f"{AV} severity_str=* | group ct=count() by severity_str",
        g, w=30, h=14,
    ))
    g.newline()

    panels.append(table(
        "PHI Access (BSI CON.3 / GDPR Art. 32)",
        (
            f"{AV} event_category='patient_access' "
            "| group ct=count() by event_type, severity_str "
            "| sort -ct"
        ),
        g, w=30, h=14,
    ))
    panels.append(table(
        "Authentication Outcomes",
        (
            f"{AV} event_category='authentication' "
            "| group ct=count() by event_type, outcome "
            "| sort -ct"
        ),
        g, w=30, h=14,
    ))
    g.newline()

    panels.append(table(
        "Administrative Changes (BSI ORP.4)",
        (
            f"{AV} event_category='administrative' "
            "| group ct=count() by event_type, outcome "
            "| sort -ct"
        ),
        g, w=30, h=14,
    ))
    panels.append(table(
        "Avelios Security Findings",
        (
            f"{AV} category_uid='2' "
            "| columns timestamp, event_type, severity_str "
            "| sort -timestamp"
        ),
        g, w=30, h=14,
    ))
    return panels


# ─── Tab 3: Omniconnect (Telematics Infrastructure) ───────────────────────
def build_omniconnect_tab() -> list:
    g = Grid()
    panels = []

    panels.append(md(
        "Omniconnect — HIS ↔ Telematics Infrastructure (TI)",
        (
            "Konnektor health, eGK / HBA / SMC-B card operations, eRezept, ePA, "
            "VSDM and KIM secure messaging.\n\n"
            "**Relevant frameworks:** gematik TI, BSI TR-03116, NIS2 Annex II."
        ),
        g, h=4, w=60,
    ))
    g.newline()

    panels.append(number("Total Omniconnect Events", f"{OC} | group ct=count()", g, suffix="", w=15, h=8))
    panels.append(number("TI Connection Events",     f"{OC} event_category='ti_connection' | group ct=count()", g, suffix="", w=15, h=8))
    panels.append(number("Card Operations",          f"{OC} event_category='card_operations' | group ct=count()", g, suffix="", w=15, h=8))
    panels.append(number("Cert / Crypto Failures",
                         f"{OC} (event_type='CERTIFICATE_EXPIRED' or event_type='CERTIFICATE_VALIDATION_FAILED' or event_type='ENCRYPTION_FAILED' or event_type='SIGNATURE_VERIFICATION_FAILED') | group ct=count()",
                         g, suffix="", w=15, h=8))
    g.newline()

    panels.append(donut(
        "Omniconnect — Event Categories",
        f"{OC} event_category=* | group ct=count() by event_category",
        g, w=30, h=14,
    ))
    panels.append(donut(
        "Omniconnect — Severity Mix",
        f"{OC} severity_str=* | group ct=count() by severity_str",
        g, w=30, h=14,
    ))
    g.newline()

    panels.append(table(
        "TI Connection Issues",
        (
            f"{OC} event_category='ti_connection' outcome!='success' "
            "| group ct=count() by event_type, severity_str "
            "| sort -ct"
        ),
        g, w=30, h=14,
    ))
    panels.append(table(
        "Card Operations (eGK / HBA / SMC-B)",
        (
            f"{OC} event_category='card_operations' "
            "| group ct=count() by event_type, outcome "
            "| sort -ct"
        ),
        g, w=30, h=14,
    ))
    g.newline()

    panels.append(table(
        "eRezept Activity",
        (
            f"{OC} event_category='erezept' "
            "| group ct=count() by event_type, outcome "
            "| sort -ct"
        ),
        g, w=30, h=14,
    ))
    panels.append(table(
        "ePA / KIM Activity",
        (
            f"{OC} (event_category='epa' or event_category='kim') "
            "| group ct=count() by event_category, event_type "
            "| sort -ct"
        ),
        g, w=30, h=14,
    ))
    return panels


# ─── Tab 4: BSI / NIS2 Compliance Findings ────────────────────────────────
def build_compliance_tab() -> list:
    g = Grid()
    panels = []

    panels.append(md(
        "BSI / NIS2 Compliance Findings",
        (
            "OCSF Security Findings (`category_uid=2`) across both healthcare "
            "platforms, mapped to BSI-Grundschutz controls and NIS2 Annex II "
            "obligations (incident handling, encryption, access control, "
            "supply-chain security)."
        ),
        g, h=4, w=60,
    ))
    g.newline()

    panels.append(number("Total Findings",        f"{HC} category_uid='2' | group ct=count()", g, suffix="", w=15, h=8))
    panels.append(number("CRITICAL Findings",     f"{HC} category_uid='2' severity_str='CRITICAL' | group ct=count()", g, suffix="", w=15, h=8))
    panels.append(number("HIGH Findings",         f"{HC} category_uid='2' severity_str='HIGH' | group ct=count()", g, suffix="", w=15, h=8))
    panels.append(number("Auth Failures (24h)",
                         f"{HC} (event_type='USER_LOGIN_FAILURE' or event_type='CARD_AUTHENTICATION_FAILED' or event_type='CARD_PIN_FAILED') | group ct=count()",
                         g, suffix="", w=15, h=8))
    g.newline()

    panels.append(stacked_bar(
        "Findings by Type per Source (NIS2 Annex II)",
        f"{HC} category_uid='2' | group ct=count() by event_type, serverHost | sort -ct",
        g, w=60, h=18, x_axis="grouped_data",
    ))
    g.newline()

    panels.append(table(
        "BSI ORP.4 — Identity & Access Anomalies",
        (
            f"{HC} (event_type='ACCOUNT_LOCKED' or event_type='UNAUTHORIZED_ACCESS_ATTEMPT' "
            "or event_type='PRIVILEGE_ESCALATION_ATTEMPT' or event_type='CARD_PIN_BLOCKED') "
            "| group ct=count() by serverHost, event_type, severity_str "
            "| sort -ct"
        ),
        g, w=30, h=14,
    ))
    panels.append(table(
        "BSI CON.1 — Crypto / Certificate Issues",
        (
            f"{HC} (event_type contains 'CERTIFICATE' or event_type contains 'ENCRYPTION' "
            "or event_type contains 'SIGNATURE') "
            "outcome!='success' "
            "| group ct=count() by serverHost, event_type, severity_str "
            "| sort -ct"
        ),
        g, w=30, h=14,
    ))
    g.newline()

    panels.append(table(
        "BSI DER.1 — Threats & Intrusions",
        (
            f"{HC} (event_type='MALWARE_DETECTED' or event_type='INTRUSION_DETECTED' "
            "or event_type='TAMPER_DETECTION' or event_type='SECURITY_POLICY_VIOLATION') "
            "| columns timestamp, serverHost, event_type, severity_str "
            "| sort -timestamp"
        ),
        g, w=30, h=14,
    ))
    panels.append(table(
        "GDPR Art. 32 — Data-Processing Events",
        (
            f"{HC} (event_type='EMERGENCY_ACCESS_OVERRIDE' or event_type='PATIENT_RECORD_DELETE' "
            "or event_type='DATA_EXPORT_INITIATED' or event_type='AUDIT_LOG_EXPORT' "
            "or event_type='EPA_EMERGENCY_ACCESS') "
            "| group ct=count() by serverHost, event_type "
            "| sort -ct"
        ),
        g, w=30, h=14,
    ))
    g.newline()

    panels.append(md(
        "Compliance Control Mapping",
        (
            "| Control | BSI / NIS2 ref | Evidence query |\n"
            "|---|---|---|\n"
            "| Identity & Access | BSI ORP.4 / NIS2 Art. 21(2)(i) | `event_category in (authentication, card_operations)` |\n"
            "| Logging & Audit | BSI OPS.1.1 / NIS2 Art. 21(2)(b) | All ingested events |\n"
            "| Cryptography | BSI CON.1 / NIS2 Art. 21(2)(h) | `event_type contains CERTIFICATE/ENCRYPTION/SIGNATURE` |\n"
            "| Incident Detection | BSI DER.1 / NIS2 Art. 21(2)(c) | `category_uid=2` |\n"
            "| Data Protection | BSI CON.3 / GDPR Art. 32 | `event_category=patient_access OR epa` |\n"
            "| Supply Chain (TI) | BSI TR-03116 / NIS2 Art. 21(2)(d) | `event_category=ti_connection` |"
        ),
        g, h=12, w=60,
    ))
    return panels


# ─── Build full tabbed dashboard ──────────────────────────────────────────
def build_overview_dashboard() -> dict:
    return {
        "configType": "TABBED",
        "duration":   "24h",
        "description": "BSI / NIS2 healthcare compliance — Avelios Medical HIS + Omniconnect TI Gateway",
        "tabs": [
            {"tabName": "Overview",    "graphs": build_overview_tab()},
            {"tabName": "Avelios HIS", "graphs": build_avelios_tab()},
            {"tabName": "Omniconnect", "graphs": build_omniconnect_tab()},
            {"tabName": "Compliance",  "graphs": build_compliance_tab()},
        ],
    }


# ─── Deploy with CAS guard + verify ───────────────────────────────────────
def deploy(c: SDLClient, path: str, dashboard: dict, canary: str) -> None:
    print(f"\n>>> Deploying {path}")
    cur_version = None
    try:
        existing = c.get_file(path)
        cur_version = existing.get("version")
        print(f"    existing version: {cur_version}")
    except Exception:
        print(f"    no existing dashboard (will create)")

    body = json.dumps(dashboard, indent=2)
    res = c.put_file(path=path, content=body, expected_version=cur_version)
    assert res.get("status") == "success", res
    new_version = res.get("version")
    print(f"    [OK] put_file  version: {cur_version} -> {new_version}  ({len(body)} bytes)")

    time.sleep(3)
    verify = c.get_file(path)
    deployed = verify.get("content", "")
    fetched_version = verify.get("version")
    if cur_version is not None:
        assert fetched_version != cur_version, "version did not bump"
    assert canary in deployed, f"canary '{canary}' not found in deployed dashboard"
    print(f"    [OK] verified by re-fetch  fetched_version={fetched_version}  canary='{canary}' present")


def main() -> int:
    c = SDLClient()
    print(f"Connected: {c.base_url}")

    dashboards_to_deploy = [
        (
            "/dashboards/bsi-nis2-healthcare-overview",
            build_overview_dashboard(),
            "BSI / NIS2 healthcare compliance",
        ),
    ]

    for path, dash, canary in dashboards_to_deploy:
        deploy(c, path, dash, canary)

    print(f"\n{'='*70}\nDONE\n{'='*70}")
    print(f"\nOpen in AI SIEM:")
    print(f"  {c.base_url}/#/dashboards")
    for path, _, _ in dashboards_to_deploy:
        print(f"  {c.base_url}/#{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
