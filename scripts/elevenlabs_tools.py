#!/usr/bin/env python3
"""Print ElevenLabs webhook tools with PUBLIC_URL filled in.

    make eleven-tools

Copy the JSON into each agent's Tools tab. Method is POST. session_id and
listing_id are dynamic variables — do not let the model invent them.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TEMPLATE = ROOT / "agent" / "elevenlabs-tools.json"
R, G, D, X = "\033[31m", "\033[32m", "\033[2m", "\033[0m"


def main() -> int:
    public = (os.getenv("PUBLIC_URL") or "").rstrip("/")
    if not public or public.startswith("https://your-"):
        print(f"{R}✗{X} PUBLIC_URL is missing or still the placeholder", file=sys.stderr)
        print(f"{D}  set it to your ngrok static domain, then re-run{X}", file=sys.stderr)
        return 1

    raw = TEMPLATE.read_text()
    filled = json.loads(raw.replace("{PUBLIC_URL}", public))
    print(json.dumps(filled, indent=2))
    print(f"\n{G}✓{X} {D}urls point at {public}{X}", file=sys.stderr)
    print(f"{D}  Renter tools: {', '.join(filled['_renter_agent'])}{X}", file=sys.stderr)
    print(f"{D}  Listing tools: {', '.join(filled['_listing_agent'])}{X}", file=sys.stderr)
    print(f"{D}  Import in ElevenLabs → Agents → Tools. Method must stay POST.{X}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
