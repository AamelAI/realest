#!/usr/bin/env python3
"""Probe every key in .env and report what it actually unlocks for this project.

    make keys

Hackathon credits are not all the same thing. Codex credits authorize the
coding agent; they do not necessarily authorize the Realtime API that carries
our calls. Find that out here, in 10 seconds, not at 13:00 on a live call.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

R, Y, G, D, X = "\033[31m", "\033[33m", "\033[32m", "\033[2m", "\033[0m"
ok = lambda m: print(f"{G}✓{X} {m}")
bad = lambda m: print(f"{R}✗{X} {m}")
meh = lambda m: print(f"{Y}!{X} {m}")
note = lambda m: print(f"  {D}{m}{X}")


def check_openai() -> bool:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    print("\nOpenAI")
    if not key:
        bad("OPENAI_API_KEY not set")
        return False
    try:
        r = httpx.get("https://api.openai.com/v1/models",
                      headers={"Authorization": f"Bearer {key}"}, timeout=15)
    except httpx.HTTPError as exc:
        bad(f"unreachable: {exc}")
        return False

    if r.status_code == 401:
        bad("401 — key rejected by the API")
        note("A Codex/ChatGPT credit grant is NOT an API key. Check platform.openai.com/api-keys")
        return False
    if r.status_code == 429:
        meh("429 — key valid but no quota on this project")
        note("Credits may be scoped to Codex, not the API. Check billing → usage limits")
        return False
    if r.status_code != 200:
        bad(f"HTTP {r.status_code}: {r.text[:160]}")
        return False

    ids = {m["id"] for m in r.json().get("data", [])}
    ok(f"API key valid · {len(ids)} models visible")

    realtime = sorted(m for m in ids if "realtime" in m)
    if realtime:
        ok(f"realtime available → {', '.join(realtime[:3])}")
        note("the voice bridge will work as designed")
    else:
        bad("NO realtime model on this key")
        note("voice falls back to Twilio <Gather>/<Say> + OpenRouter — see docs/VOICE_FALLBACK.md")

    # Structured outputs ride on normal chat models; confirm at least one exists.
    if any(m.startswith(("gpt-4", "gpt-5", "o")) for m in ids):
        ok("chat models available → CallOutcome extraction fine")
    else:
        meh("no obvious chat model; route extraction through OpenRouter instead")
    return bool(realtime)


def check_openrouter() -> None:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    print("\nOpenRouter")
    if not key:
        bad("OPENROUTER_API_KEY not set")
        return
    try:
        r = httpx.get("https://openrouter.ai/api/v1/key",
                      headers={"Authorization": f"Bearer {key}"}, timeout=15)
    except httpx.HTTPError as exc:
        bad(f"unreachable: {exc}")
        return
    if r.status_code != 200:
        bad(f"HTTP {r.status_code}: {r.text[:160]}")
        return

    d = r.json().get("data", {})
    limit, used = d.get("limit"), d.get("usage")
    ok("key valid")
    if limit is None:
        note(f"usage ${used or 0:.2f} · no hard limit set")
    else:
        note(f"usage ${used or 0:.2f} of ${limit:.2f}")
    if d.get("is_free_tier"):
        meh("free tier — only :free models, low daily cap")
    note("use for: ranking rationale, call summarization, email drafting, CallOutcome fallback")


def check_exa() -> None:
    key = os.getenv("EXA_API_KEY", "").strip()
    print("\nExa")
    if not key:
        bad("EXA_API_KEY not set")
        return
    try:
        r = httpx.post("https://api.exa.ai/search",
                       headers={"x-api-key": key, "Content-Type": "application/json"},
                       json={"query": "Liberty Village Toronto transit", "numResults": 1},
                       timeout=20)
    except httpx.HTTPError as exc:
        bad(f"unreachable: {exc}")
        return
    if r.status_code != 200:
        bad(f"HTTP {r.status_code}: {r.text[:160]}")
        return
    n = len(r.json().get("results", []))
    ok(f"key valid · search returned {n} result(s)")
    note("use for: card enrichment — transit, building reputation, neighbourhood")


def check_twilio() -> None:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    tok = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    print("\nTwilio")
    if not (sid and tok):
        bad("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not set")
        return
    try:
        r = httpx.get(f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
                      auth=(sid, tok), timeout=15)
    except httpx.HTTPError as exc:
        bad(f"unreachable: {exc}")
        return
    if r.status_code != 200:
        bad(f"HTTP {r.status_code} — check SID/token")
        return
    acct = r.json()
    ok(f"account valid · {acct.get('friendly_name', '')}")
    if acct.get("type") == "Trial":
        meh("TRIAL account")
        note("only VERIFIED numbers can be called, and every SMS is prefixed")
        note("Console → Phone Numbers → Verified Caller IDs")
    else:
        ok("full account — no verified-number restriction")


if __name__ == "__main__":
    print(f"{D}probing keys in .env …{X}")
    realtime = check_openai()
    check_openrouter()
    check_exa()
    check_twilio()
    print()
    if not realtime:
        print(f"{Y}→ Realtime unavailable. Read docs/VOICE_FALLBACK.md before 11:15.{X}")
    sys.exit(0)
