#!/usr/bin/env python3
"""Connectivity spike: can we place a phone call at all?

    make spike TO=+14165551234

This is a setup check, like doctor.py - not product code. It proves the Twilio
number, the provider account, the agent and the phone number import are all
wired together. The real call orchestration (fan-out, timeouts, CallOutcome
extraction, re-ranking) is built during the event in server/calls.py.

Run it the moment you have keys. Until your own phone rings, nothing else in
the telephony lane matters.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

R, Y, G, D, X = "\033[31m", "\033[33m", "\033[32m", "\033[2m", "\033[0m"
E164 = re.compile(r"^\+[1-9]\d{7,14}$")

# ElevenLabs Conversational AI. Vapi/Retell differ only in URL and payload keys -
# the shape (one POST, agent id + number id + destination) is the same everywhere.
OUTBOUND_URL = "https://api.elevenlabs.io/v1/convai/twilio/outbound-call"
CONVERSATION_URL = "https://api.elevenlabs.io/v1/convai/conversations/{cid}"


def need(key: str) -> str:
    v = os.getenv(key, "").strip()
    if not v:
        print(f"{R}✗{X} {key} not set in .env")
        sys.exit(1)
    return v


def main() -> int:
    ap = argparse.ArgumentParser(description="Place one test call")
    ap.add_argument("--to", required=True, help="your own phone, E.164, e.g. +14165551234")
    ap.add_argument("--agent", default="renter", choices=["renter", "listing"])
    ap.add_argument("--status", metavar="CONVERSATION_ID",
                    help="skip the call, just fetch status + transcript for this id")
    args = ap.parse_args()

    api_key = need("VOICE_API_KEY")
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

    if args.status:
        with httpx.Client(timeout=20) as c:
            r = c.get(CONVERSATION_URL.format(cid=args.status), headers=headers)
        print(json.dumps(r.json(), indent=2)[:3000])
        return 0 if r.status_code == 200 else 1

    if not E164.match(args.to):
        print(f"{R}✗{X} --to must be E.164 (e.g. +14165551234), got {args.to!r}")
        return 1

    agent_id = need("VOICE_RENTER_AGENT_ID" if args.agent == "renter" else "VOICE_LISTING_AGENT_ID")
    number_id = need("VOICE_PHONE_NUMBER_ID")

    payload = {
        "agent_id": agent_id,
        "agent_phone_number_id": number_id,
        "to_number": args.to,
        # These come back on the outcome webhook and are how you know which card
        # to update. Getting them wrong means three calls writing to one listing.
        "conversation_initiation_client_data": {
            "dynamic_variables": {
                "session_id": "spike",
                "listing_id": "L001",
                "listing_address": "25 Ordnance Street",
                "listed_rent": "2495",
                "extra_questions": "is there a locker",
            }
        },
    }

    print(f"{D}→ {args.agent} agent calling {args.to}…{X}")
    try:
        with httpx.Client(timeout=30) as c:
            r = c.post(OUTBOUND_URL, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        print(f"{R}✗{X} request failed: {exc}")
        return 1

    if r.status_code != 200:
        print(f"{R}✗{X} HTTP {r.status_code}\n{r.text[:600]}")
        print(f"\n{D}Common causes:{X}")
        print(f"{D}  401/403  wrong VOICE_API_KEY{X}")
        print(f"{D}  404      wrong agent id or phone number id{X}")
        print(f"{D}  400      number not imported provider-side, or --to not verified{X}")
        print(f"{D}           on a Twilio trial (verify it in the Twilio console){X}")
        return 1

    data = r.json()
    cid = data.get("conversation_id", "")
    print(f"{G}✓{X} call placed")
    print(f"  conversation  {cid}")
    print(f"  call sid      {data.get('callSid', '—')}")
    print(f"\n{D}Your phone should ring. Say something that would fire a tool.{X}")
    print(f"{D}Then: uv run python scripts/spike_call.py --to {args.to} --status {cid}{X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
