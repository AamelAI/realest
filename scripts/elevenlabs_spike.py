#!/usr/bin/env python3
"""Place one outbound call through the ElevenLabs provider.

    make eleven-spike TO=+14165551234              # listing-agent voice
    make eleven-spike TO=+14165551234 ROLE=renter  # renter-facing voice

Uses the same ElevenLabsProvider the server will import later. Does not
touch calls.place_call or the OpenAI Realtime bridge.

Requires the four ELEVENLABS_* keys in .env — see docs/ELEVENLABS.md.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "server"))

from voice.elevenlabs import ElevenLabsError, ElevenLabsProvider  # noqa: E402

R, G, D, X = "\033[31m", "\033[32m", "\033[2m", "\033[0m"
E164 = re.compile(r"^\+[1-9]\d{7,14}$")

CHECKLIST = """
ElevenLabs is not configured yet. Do this, then re-run:

  1. Create an account at elevenlabs.io — pick ElevenAgents
  2. Profile → API Keys → copy into ELEVENLABS_API_KEY
  3. Phone Numbers → import your Twilio number → ELEVENLABS_PHONE_NUMBER_ID
  4. Create a renter agent and a listing agent → the two AGENT_ID keys
  5. Paste all four into .env

Full runbook: docs/ELEVENLABS.md
""".strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Place one ElevenLabs test call")
    ap.add_argument("--to", required=True, help="your own phone, E.164, e.g. +14165551234")
    ap.add_argument("--role", default="listing", choices=["listing", "renter"])
    args = ap.parse_args()

    if not E164.match(args.to):
        print(f"{R}✗{X} --to must be E.164 (e.g. +14165551234), got {args.to!r}")
        return 1

    provider = ElevenLabsProvider()
    if not provider.configured():
        print(f"{R}✗{X} missing {', '.join(provider.missing())}")
        print(f"\n{D}{CHECKLIST}{X}")
        return 1

    print(f"{D}  ElevenLabsProvider · {args.role} → {args.to}{X}")
    try:
        handle = asyncio.run(provider.place_outbound(
            to_number=args.to,
            role=args.role,
            dynamic_variables={
                "spike": "1",
                "role": args.role,
                "session_id": "spike",
                "listing_id": "SPIKE",
                "address": "700 Wellington St W (spike)",
                "listing_address": "700 Wellington St W (spike)",
                "listed_rent": "2800",
                "agent_name": "Dana",
                "extra_questions": "",
            },
        ))
    except ElevenLabsError as exc:
        print(f"{R}✗{X} {exc}")
        return 1

    print(f"{G}✓{X} call placed · conversation {handle.conversation_id} · sid {handle.call_sid}")
    print(f"\n{D}Your phone should ring and the agent should speak first.{X}")
    print(f"{D}Interrupt it mid-sentence — it must stop talking.{X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
