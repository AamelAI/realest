#!/usr/bin/env python3
"""Place one outbound call through Twilio, bridged to OpenAI Realtime.

    make spike TO=+14165551234              # listing-agent voice (the differentiator)
    make spike TO=+14165551234 ROLE=renter  # renter-facing voice

Setup check, like doctor.py - not product code. It proves the Twilio number,
the tunnel, the bridge and your OpenAI key are all wired together. The real
orchestration (fan-out, timeouts, CallOutcome, re-ranking) is built during the
event in server/calls.py.

Requires scripts/spike_bridge.py running and `make tunnel` up.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from twilio.rest import Client

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

R, G, D, X = "\033[31m", "\033[32m", "\033[2m", "\033[0m"
E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def need(key: str) -> str:
    v = os.getenv(key, "").strip()
    if not v:
        print(f"{R}✗{X} {key} not set in .env")
        sys.exit(1)
    return v


def main() -> int:
    ap = argparse.ArgumentParser(description="Place one test call")
    ap.add_argument("--to", required=True, help="your own phone, E.164, e.g. +14165551234")
    ap.add_argument("--role", default="listing", choices=["listing", "renter"])
    args = ap.parse_args()

    if not E164.match(args.to):
        print(f"{R}✗{X} --to must be E.164 (e.g. +14165551234), got {args.to!r}")
        return 1

    sid, token = need("TWILIO_ACCOUNT_SID"), need("TWILIO_AUTH_TOKEN")
    from_ = need("TWILIO_PHONE_NUMBER")
    public = need("PUBLIC_URL").rstrip("/")

    # The bridge has to be reachable before Twilio tries. Fail here, not mid-call.
    try:
        r = httpx.get(f"{public}/health", timeout=8)
        r.raise_for_status()
        print(f"{D}  bridge ok · model {r.json().get('model')}{X}")
    except Exception as exc:
        print(f"{R}✗{X} {public}/health unreachable: {exc}")
        print(f"{D}  → is `make bridge` running, and `make tunnel` up on the same port?{X}")
        return 1

    try:
        call = Client(sid, token).calls.create(
            to=args.to, from_=from_, url=f"{public}/twiml/{args.role}"
        )
    except Exception as exc:
        msg = str(exc)
        print(f"{R}✗{X} {msg[:400]}")
        if "21219" in msg or "unverified" in msg.lower():
            print(f"{D}  → trial accounts only call VERIFIED numbers.{X}")
            print(f"{D}    Twilio Console → Phone Numbers → Verified Caller IDs{X}")
        elif "21606" in msg or "21210" in msg:
            print(f"{D}  → TWILIO_PHONE_NUMBER isn't a voice-capable number on this account{X}")
        return 1

    print(f"{G}✓{X} call placed · sid {call.sid} · {args.role} voice")
    print(f"\n{D}Your phone should ring and the agent should speak first.{X}")
    print(f"{D}Interrupt it mid-sentence - it must stop talking. That's barge-in working.{X}")
    print(f"{D}Transcripts print in the bridge terminal.{X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
