#!/usr/bin/env python3
"""Hit start_calls directly with a custom payload. No renter agent.

    uv run python scripts/test_start_calls.py
    uv run python scripts/test_start_calls.py --listing-ids L100 --extra-questions 'are dogs allowed'
    uv run python scripts/test_start_calls.py --to +14375550100 --listing-ids L100,L086
    uv run python scripts/test_start_calls.py --http --listing-ids L100
    uv run python scripts/test_start_calls.py --stub --listing-ids L095
    uv run python scripts/test_start_calls.py --field pets=dog --field beds=2

    make start-call LISTING=L100 Q='are dogs allowed'
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "server"))

R, G, D, Y, X = "\033[31m", "\033[32m", "\033[2m", "\033[33m", "\033[0m"


def _coerce(raw: str):
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
        return int(raw)
    if raw[:1] in "[{":
        return json.loads(raw)
    return raw


def _fields(pairs: list[str]) -> dict:
    out: dict = {}
    for item in pairs:
        if "=" not in item:
            raise SystemExit(f"{R}✗{X} --field needs key=value, got {item!r}")
        k, v = item.split("=", 1)
        out[k.strip()] = _coerce(v.strip())
    return out


def build_payload(args: argparse.Namespace) -> dict:
    payload = _fields(args.field)
    if args.session_id:
        payload["session_id"] = args.session_id
    if args.listing_ids:
        payload["listing_ids"] = args.listing_ids
    if args.extra_questions:
        payload["extra_questions"] = args.extra_questions
    if args.caller:
        payload["caller_phone"] = args.caller
    return payload


def main() -> int:
    demo = os.getenv("DEMO_AGENT_PHONE", "").strip() or "+14375550100"
    ap = argparse.ArgumentParser(description="Call start_calls with custom fields")
    ap.add_argument("--session-id", default="", help="Reuse a session. Minted if omitted.")
    ap.add_argument("--listing-ids", default="", help="CSV, e.g. L100 or L100,L086")
    ap.add_argument("--extra-questions", default="", help="CSV of extra asks for the listing agent")
    ap.add_argument("--caller", default="", help="Renter E.164, if you want SMS / session reuse")
    ap.add_argument("--to", default=demo, help=f"Listing-agent number to ring (default {demo})")
    ap.add_argument("--field", action="append", default=[], metavar="KEY=VALUE",
                    help="Any extra body field. Repeatable. JSON/bool/int coerced.")
    ap.add_argument("--http", action="store_true",
                    help="POST the running server (localhost:8000 or --url) instead of in-process")
    ap.add_argument("--url", default=os.getenv("PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/"),
                    help="Base URL for --http")
    ap.add_argument("--stub", action="store_true", help="Force TRANSPORT=stub (no phone)")
    ap.add_argument("--live", action="store_true", help="Force TRANSPORT=voice (will ring --to)")
    ap.add_argument("--dry", action="store_true", help="Print the payload and dest, do not call")
    ap.add_argument("--no-seed", action="store_true",
                    help="Do not seed preferences when listing_ids is empty")
    args = ap.parse_args()

    if args.stub and args.live:
        print(f"{R}✗{X} pick --stub or --live, not both")
        return 1
    if args.stub:
        os.environ["TRANSPORT"] = "stub"
    if args.live:
        os.environ["TRANSPORT"] = "voice"
    os.environ.setdefault("FORCE_BUSINESS_HOURS", "1")
    if args.to:
        os.environ["DEMO_AGENT_PHONE"] = args.to

    payload = build_payload(args)
    mode = os.getenv("TRANSPORT", "stub")
    print(f"{D}  transport={mode}  provider={os.getenv('VOICE_PROVIDER', '') or '—'}  to={args.to}{X}")
    print(f"{D}  payload {json.dumps(payload, indent=2)}{X}")
    if args.dry:
        return 0
    if mode == "voice":
        print(f"{Y}! ringing {args.to} — the listing phone should get a call{X}")

    if args.http:
        return _via_http(args.url, payload)
    return asyncio.run(_via_import(args, payload))


def _via_http(url: str, payload: dict) -> int:
    import httpx
    dest = f"{url.rstrip('/')}/agent/start-calls"
    print(f"{D}  POST {dest}{X}")
    try:
        r = httpx.post(dest, json=payload, timeout=130)
    except Exception as exc:
        print(f"{R}✗{X} {exc}")
        print(f"{D}  → is `make dev` running? for the tunnel path, is `make tunnel` up?{X}")
        return 1
    print(f"{D}  HTTP {r.status_code}{X}")
    try:
        body = r.json()
        print(json.dumps(body, indent=2))
    except Exception:
        print(r.text[:800])
        return 1
    return 0 if r.is_success else 1


async def _via_import(args: argparse.Namespace, payload: dict) -> int:
    import calls
    import main
    import state as store
    import transport
    from schemas import CallStatus

    print(f"{D}  in-process  is_stub={transport.is_stub()}{X}")

    sid = payload.get("session_id") or "start-call-test"
    payload["session_id"] = sid
    raw_ids = main._as_list(payload.get("listing_ids"))
    if raw_ids:
        from schemas import ListingState
        import listings as L

        def pin(st):
            have = {x.listing_id for x in st.listings}
            for lid in raw_ids:
                if lid in have or not L.by_id(lid):
                    continue
                st.listings.append(ListingState(listing_id=lid, rank=len(st.listings) + 1))

        await store.mutate(sid, pin)
        print(f"{D}  pinned listings {raw_ids} on session {sid}{X}")

    if not payload.get("listing_ids") and not args.no_seed:
        sid = payload.get("session_id") or "start-call-test"
        payload["session_id"] = sid
        seed = {
            "session_id": sid,
            "beds": 2,
            "areas": ["downtown"],
            "max_rent": 3000,
        }
        extra = {k: payload[k] for k in ("beds", "areas", "max_rent", "pets", "parking") if k in payload}
        seed.update(extra)
        print(f"{D}  seeding preferences {seed}{X}")
        await main.agent_preferences(seed)

    try:
        result = await main.agent_start_calls(payload)
    except Exception as exc:
        print(f"{R}✗{X} start_calls raised: {exc}")
        return 1

    print(f"{G}✓{X} {json.dumps(result, indent=2)}")
    sid = result.get("session_id")
    s = store.get(sid) if sid else None
    if s:
        print(f"{D}  session {sid}  dest={calls.destination(sid, None)}  says={s.agent_says!r}{X}")
        for st in s.listings:
            oc = "outcome" if st.outcome else "—"
            print(f"    {st.listing_id:<6}  {st.status.name:<12}  {oc}  {st.email_draft and 'email' or ''}")
        pending = [st.listing_id for st in s.listings if st.status is CallStatus.PENDING]
        dialed = [st.listing_id for st in s.listings if st.status is not CallStatus.PENDING]
        if pending and dialed:
            print(f"{D}  dialed {dialed}  skipped {pending}{X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
