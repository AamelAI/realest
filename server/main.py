"""FastAPI - the whole backend.

Every voice-agent tool is dispatched here IN-PROCESS (see bridge.py). Every
handler returns a short string the agent reads ALOUD: keep it under 25 words
and write it as speech.

You can build and test ~90% of this with curl, no phone involved. Do that.
"""
from __future__ import annotations

import asyncio
import logging
import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import calls
import listings as L
import state as store
from schemas import CallOutcome, CallStatus, Preferences

log = logging.getLogger("realest.main")

load_dotenv()

app = FastAPI(title="Realest", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Three call outcomes land within a second of each other. rerank() reads state,
# computes an order, then writes it - all outside store's lock - so two
# concurrent re-ranks clobber each other and the last writer wins, silently
# dropping the other calls' results. Serialise apply+rerank.
_outcome_lock = asyncio.Lock()

WEB_URL = os.getenv("WEB_URL", "http://localhost:3000").rstrip("/")
SHORTLIST_SIZE = 4


@app.get("/health")
def health():
    import transport
    import voice
    return {
        "status": "ok",
        "listings": len(L.load()),
        "sessions": len(store.all_ids()),
        "transport": transport.mode(),
        "voice_provider": voice.provider_name(),
    }


# ── reading ──────────────────────────────────────────────────────────────────

def _cards(session) -> list[dict]:
    """Join each ListingState with its Listing. The page never fetches twice."""
    catalogue = {l.listing_id: l for l in L.load()}
    out: list[dict] = []
    for st in session.listings:
        lst = catalogue.get(st.listing_id)
        if lst is None:
            continue
        card = lst.model_dump(mode="json")
        card.pop("agent_phone", None)      # never ships to the browser
        card.pop("agent_email", None)
        card.update(st.model_dump(mode="json"))
        out.append(card)
    return out


@app.get("/api/state")
async def read_state(session: str):
    """The page polls this every 1-1.5s. Rank on write, never on read."""
    s = store.get(session)
    if s is None:
        return {"session_id": session, "preferences": {}, "listings": [],
                "agent_says": "", "updated_at": 0.0}
    return {
        "session_id": s.session_id,
        "preferences": s.preferences.model_dump(mode="json"),
        "listings": _cards(s),
        "agent_says": s.agent_says,
        "updated_at": s.updated_at,
    }


# ── the one re-rank path everything funnels through ──────────────────────────

async def rerank(session_id: str, says: str | None = None, shortlist: bool = True):
    """Rank the whole list, every time. Two triggers only: prefs, and an outcome."""
    s = store.get(session_id)
    prefs = s.preferences if s else Preferences()
    outcomes = {st.listing_id: st.outcome for st in (s.listings if s else []) if st.outcome}

    pool = L.load()
    if s and s.listings:
        # Already shortlisted: re-rank exactly those, never widen mid-conversation.
        keep = {st.listing_id for st in s.listings}
        pool = [l for l in pool if l.listing_id in keep]

    ranked = L.rank(pool, prefs, outcomes, previous=s.listings if s else None)
    if shortlist and (not s or not s.listings):
        ranked = ranked[:SHORTLIST_SIZE]
        for i, st in enumerate(ranked, start=1):
            st.rank = i

    line = says if says is not None else L.explain(ranked, outcomes, prefs)

    def write(st_):
        st_.listings = ranked
        st_.agent_says = line

    return await store.mutate(session_id, write)


# ── writing: every voice tool lands on one of these ──────────────────────────

def _nested_get(payload: dict, *keys: str) -> str:
    """First non-empty string among top-level keys or common ElevenLabs wrappers."""
    wrappers = [payload]
    for wrap in ("data", "conversation_initiation_client_data", "dynamic_variables"):
        inner = payload.get(wrap)
        if isinstance(inner, dict):
            wrappers.append(inner)
    for block in wrappers:
        for key in keys:
            val = block.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
    return ""


def _ensure_session(payload: dict) -> str:
    """Stable session id for webhook tools. Never invent listing facts here."""
    sid = _nested_get(payload, "session_id")
    if not sid:
        sid = _nested_get(payload, "conversation_id")
    if not sid:
        sid = secrets.token_urlsafe(6)
        log.info("session minted %s", sid)
    return sid


def _apply_caller(payload: dict) -> str:
    phone = _nested_get(payload, "caller_phone", "From", "from_number", "user_id")
    return phone if phone and calls.E164.match(phone) else ""


@app.post("/agent/preferences")
async def agent_preferences(payload: dict):
    """Caller described what they want, or reprioritized. Re-rank, speak one line."""
    sid = _ensure_session(payload)
    first = store.get(sid) is None
    fields = {k: v for k, v in payload.items() if k in Preferences.model_fields and v is not None}
    phone = _apply_caller(payload)

    def write(s):
        s.preferences = s.preferences.model_copy(update=fields)
        if phone and not s.caller_phone:
            s.caller_phone = phone

    await store.mutate(sid, write)
    if first:
        asyncio.create_task(calls.sms_if_call_alive(sid, f"{WEB_URL}/s/{sid}"))
    s = await rerank(sid, says="")
    n = len(s.listings)
    top = L.by_id(s.listings[0].listing_id).address.split(",")[0] if n else ""
    spoken = (f"{n} fit. I've texted you a link - {top} is on top. Have a look while we talk."
              if n else "Nothing matches that yet. Want to widen the budget or the area?")
    await store.mutate(sid, lambda s_: setattr(s_, "agent_says", spoken))
    # The model needs the ids to pass back to start_calls. They are never
    # spoken - `speak` is the only field that reaches the caller's ear - but
    # without them the model invents labels like "Listing 2" and nothing matches.
    shortlist = [
        {"listing_id": st.listing_id,
         "address": (L.by_id(st.listing_id).address if L.by_id(st.listing_id) else "")}
        for st in s.listings
    ]
    return {"speak": spoken, "session_id": sid, "count": n,
            "link": f"{WEB_URL}/s/{sid}", "shortlist": shortlist}


def _resolve_ids(raw: list, session_id: str) -> list[str]:
    """Map whatever the model sent back to real listing ids.

    It is given the ids in the record_preferences result, but models still
    sometimes echo an address or a label. Silently calling nothing is the worst
    outcome, so match on id first, then address, then fall back to the whole
    shortlist if nothing resolves.
    """
    s = store.get(session_id)
    known = [st.listing_id for st in s.listings] if s else []
    if not raw:
        return known
    out: list[str] = []
    for item in raw:
        token = str(item).strip()
        if token in known:
            out.append(token)
            continue
        low = token.lower()
        for lid in known:
            lst = L.by_id(lid)
            if lst and (low in lst.address.lower() or lst.address.lower() in low):
                out.append(lid)
                break
    return out or known


def _resolve_listing_id(payload: dict, session_id: str) -> str:
    raw = _nested_get(payload, "listing_id")
    if raw and L.by_id(raw):
        return raw
    if raw:
        found = _resolve_ids([raw], session_id)
        if found:
            return found[0]
    addr = _nested_get(payload, "address")
    if addr:
        found = _resolve_ids([addr], session_id)
        if found:
            return found[0]
    return ""


@app.post("/agent/start-calls")
async def agent_start_calls(payload: dict):
    """Verify these listings. Fan out. Cards flip to CALLING before any await."""
    sid = _ensure_session(payload)
    ids = _resolve_ids(payload.get("listing_ids") or [], sid)
    extra = payload.get("extra_questions") or []
    phone = _apply_caller(payload)

    if not calls.within_business_hours():
        spoken = calls.OUT_OF_HOURS
        await store.mutate(sid, lambda s: setattr(s, "agent_says", spoken))
        await calls.email_all(sid, ids, extra)
        return {"speak": spoken, "session_id": sid, "called": 0, "emailed": len(ids)}

    def write(s):
        if extra:
            s.preferences.extra_questions = extra
        if phone and not s.caller_phone:
            s.caller_phone = phone
        for st in s.listings:
            if st.listing_id in ids:
                st.status = CallStatus.CALLING

    n = len(ids)
    spoken = f"Calling {'all ' + str(n) if n > 1 else 'them'} now - watch your screen."
    await store.mutate(sid, write)
    await store.mutate(sid, lambda s: setattr(s, "agent_says", spoken))
    await calls.fan_out(sid, ids, extra)
    return {"speak": spoken, "session_id": sid, "called": n}


@app.post("/agent/outcome")
async def agent_outcome(payload: dict):
    """A listing agent told us something. Write it, then RE-RANK THE WHOLE LIST."""
    sid = _ensure_session(payload)
    lid = _resolve_listing_id(payload, sid)
    log.info("outcome[%s] listing=%s", sid, lid or "?")
    if not lid:
        return {"speak": "Got it.", "session_id": sid}

    s = store.get(sid)
    existing = next((st for st in (s.listings if s else []) if st.listing_id == lid), None)
    if existing and existing.outcome is not None:
        return {"speak": "Got it.", "session_id": sid, "agent_says": s.agent_says if s else ""}

    oc = CallOutcome(**{k: v for k, v in payload.items()
                        if k in CallOutcome.model_fields and v is not None})

    def write(st_):
        for st in st_.listings:
            if st.listing_id == lid:
                L.apply_outcome(st, oc)

    async with _outcome_lock:
        await store.mutate(sid, write)
        s = await rerank(sid)
    return {"speak": "Got it, thanks.", "session_id": sid, "agent_says": s.agent_says}


@app.post("/agent/book")
async def agent_book(payload: dict):
    """Plain code does the write - the model only calls this."""
    sid = _ensure_session(payload)
    lid = _resolve_listing_id(payload, sid)
    slot = payload.get("slot", "")
    lst = L.by_id(lid)
    where = lst.address.split(",")[0] if lst else "it"
    spoken = f"Booked - {where}, {slot}. Confirmation is on its way by text."

    def write(s):
        for st in s.listings:
            if st.listing_id == lid:
                st.status = CallStatus.BOOKED
                if st.outcome:
                    st.outcome.viewing_slot = slot
        s.agent_says = spoken

    await store.mutate(sid, write)
    await calls.sms(sid, f"Confirmed: {where}, {slot}. {WEB_URL}/s/{sid}")
    return {"speak": spoken, "session_id": sid}


@app.post("/agent/email")
async def agent_email(payload: dict):
    """Caller tapped Send on a drafted email. Plain code, no model in the loop."""
    sid = _ensure_session(payload)
    lid = _resolve_listing_id(payload, sid)
    sent = await calls.send_email(sid, lid)
    return {"sent": sent, "session_id": sid}


# The voice layer: TwiML + the media websocket, mounted on this same app so a
# tool call writes SessionState in-process with no HTTP hop and one tunnel.
import bridge  # noqa: E402

bridge.attach(app)

# The text layer. Same prompt, same tools, same dispatch() - only the transport
# differs, so the whole product can be exercised by typing while voice lands in
# parallel. GET /chat is a harness page; POST /chat is one turn.
import chat  # noqa: E402

chat.attach(app)
