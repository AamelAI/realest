#!/usr/bin/env python3
"""Check this machine is ready to build. Run before doors, and again at 11:15.

    make doctor
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R, Y, G, D, X = "\033[31m", "\033[33m", "\033[32m", "\033[2m", "\033[0m"
ok = lambda m: print(f"{G}✓{X} {m}")
bad = lambda m, fix: print(f"{R}✗{X} {m}\n  {D}→ {fix}{X}")
meh = lambda m, fix: print(f"{Y}!{X} {m}\n  {D}→ {fix}{X}")

REQUIRED_KEYS = [
    "OPENAI_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER", "PUBLIC_URL", "WEB_URL",
]
NICE_KEYS = ["OPENROUTER_API_KEY", "EXA_API_KEY", "RESEND_API_KEY"]


def tool(name: str, fix: str) -> bool:
    if shutil.which(name):
        try:
            v = subprocess.run([name, "--version"], capture_output=True, text=True,
                               timeout=5).stdout.strip().splitlines()[0]
        except Exception:
            v = ""
        ok(f"{name} {D}{v}{X}")
        return True
    bad(f"{name} not found", fix)
    return False


def main() -> int:
    fails = 0
    print(f"{D}{platform.system()} {platform.machine()} · python {platform.python_version()}{X}\n")

    if platform.system() == "Darwin" and platform.machine() == "x86_64":
        print(f"{D}Intel Mac — cryptography is pinned <47 for you. Don't relax it.{X}\n")

    fails += not tool("uv", "curl -LsSf https://astral.sh/uv/install.sh | sh")
    fails += not tool("node", "https://nodejs.org or `brew install node`")
    if shutil.which("ngrok"):
        v = subprocess.run(["ngrok", "version"], capture_output=True, text=True).stdout.strip()
        try:
            major, minor = (int(x) for x in v.split()[-1].split(".")[:2])
            if (major, minor) < (3, 20):
                bad(f"{v} — too old", "ngrok update  (accounts require 3.20+; free tier is NOT exempt)")
                fails += 1
            else:
                ok(f"ngrok {D}{v}{X}")
        except Exception:
            ok(f"ngrok {D}{v}{X}")
    else:
        bad("ngrok not found", "brew install ngrok && ngrok config add-authtoken <token>")
        fails += 1

    if sys.version_info[:2] != (3, 12):
        meh(f"running python {platform.python_version()}, repo pins 3.12",
            "run through `uv run`, not bare python")
    else:
        ok("python 3.12")

    env = ROOT / ".env"
    if not env.exists():
        bad(".env missing", "cp .env.example .env, then fill it in")
        fails += 1
    else:
        vals = {}
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                vals[k.strip()] = v.strip()
        missing = [k for k in REQUIRED_KEYS if not vals.get(k)]
        if missing:
            bad(f".env missing {len(missing)} required key(s): {', '.join(missing)}",
                "see .env.example for where each one comes from")
            fails += 1
        else:
            ok(f".env — all {len(REQUIRED_KEYS)} required keys set")
        absent = [k for k in NICE_KEYS if not vals.get(k)]
        if absent:
            meh(f"optional keys unset: {', '.join(absent)}", "fine for now, needed for P2")
        if vals.get("PUBLIC_URL", "").startswith("https://your-"):
            bad("PUBLIC_URL is still the placeholder",
                "set it to your ngrok URL and paste that into agent/tools.json")
            fails += 1

    listings = ROOT / "data" / "listings.json"
    if not listings.exists():
        bad("data/listings.json missing",
            "cp data/listings.sample.json data/listings.json, expand to ~50, then `make seed`")
        fails += 1
    else:
        rows = json.loads(listings.read_text())
        phones = {r.get("agent_phone", "") for r in rows}
        if any("REPLACE" in p for p in phones):
            bad("listings still contain placeholder phone numbers", "`make check` will list them")
            fails += 1
        elif len(rows) < 20:
            meh(f"only {len(rows)} listings", "aim for ~50 so the shortlist can move")
        else:
            ok(f"{len(rows)} listings, {len(phones)} distinct numbers")

    pub = (vals.get("PUBLIC_URL", "") if env.exists() else "")
    if pub and not pub.startswith("https://your-"):
        try:
            import urllib.request
            urllib.request.urlopen(pub + "/health", timeout=6)
            ok(f"bridge reachable at {pub}")
        except Exception:
            meh(f"{pub}/health unreachable", "start `make bridge` and `make tunnel`")

    if (ROOT / "web" / "node_modules").exists():
        ok("web deps installed")
    else:
        meh("web/node_modules missing", "make install")

    print()
    if fails:
        print(f"{R}{fails} blocker(s).{X} Fix these before 11:15.")
        return 1
    print(f"{G}Ready.{X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
