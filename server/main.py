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

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import admin as monitor
import calls
import listings as L
import state as store
from schemas import CallOutcome, CallStatus, ListingState, Preferences

_STATIC = Path(__file__).resolve().parent / "static"

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

# sessions that have already been sent their shortlist link
_linked: set[str] = set()

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


@app.get("/admin")
@app.get("/admin/")
async def admin_page():
    """Browser UI for the live/history monitor (same origin as /admin/* APIs)."""
    return FileResponse(_STATIC / "admin.html")


@app.get("/admin/live")
async def admin_live():
    return await monitor.live_payload()


@app.get("/admin/calls")
async def admin_calls(limit: int = 20):
    return await monitor.history_payload(max(1, min(limit, 50)))


@app.get("/admin/calls/{conversation_id}")
async def admin_call_detail(conversation_id: str):
    return await monitor.detail_payload(conversation_id)


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
    for wrap in ("data", "conversation_initiation_client_data", "dynamic_variables",
                 "parameters", "arguments", "tool_parameters"):
        inner = payload.get(wrap)
        if isinstance(inner, dict):
            wrappers.append(inner)
    for block in wrappers:
        for key in keys:
            val = block.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
    return ""


def _walk_dicts(obj, depth: int = 0):
    if depth > 6 or not isinstance(obj, dict):
        return
    yield obj
    for val in obj.values():
        if isinstance(val, dict):
            yield from _walk_dicts(val, depth + 1)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    yield from _walk_dicts(item, depth + 1)


_CALLER_KEYS = (
    "caller_phone", "caller_id", "system__caller_id", "from_number",
    "From", "from", "caller", "user_id",
)


def _apply_caller(payload: dict) -> str:
    """Inbound caller as E.164. Accepts +1416…, 4165550101, or (416) 555-0101."""
    if not isinstance(payload, dict):
        return ""
    for block in _walk_dicts(payload):
        for key in _CALLER_KEYS:
            dest = calls.as_e164(str(block.get(key) or ""))
            if dest:
                return dest
    return ""


async def _request_payload(request: Request) -> dict:
    """Init webhook may be JSON, form, or query — do not drop the caller_id."""
    payload: dict = {}
    try:
        body = await request.json()
        if isinstance(body, dict):
            payload = body
    except Exception:
        payload = {}
    if not payload:
        payload = {k: v for k, v in request.query_params.multi_items()}
        try:
            form = await request.form()
            payload.update({k: str(v) for k, v in form.multi_items()})
        except Exception:
            pass
    return payload


def _session_for_caller(phone: str) -> str:
    """Reuse the inbound session minted at pickup when a tool omits session_id."""
    if not phone:
        return ""
    best, best_t = "", -1.0
    for sid in store.all_ids():
        s = store.get(sid)
        if s and s.caller_phone == phone and s.updated_at >= best_t:
            best, best_t = sid, s.updated_at
    return best


def _ensure_session(payload: dict) -> str:
    """Stable session id for webhook tools. Never invent listing facts here."""
    sid = _nested_get(payload, "session_id")
    if not sid:
        sid = _nested_get(payload, "conversation_id")
    if not sid:
        sid = _session_for_caller(_apply_caller(payload))
    if not sid:
        sid = secrets.token_urlsafe(6)
        log.info("session minted %s", sid)
    return sid


async def _sms_link_once(sid: str, link: str, to: str = "") -> bool:
    """One shortlist text per session. Safe to call from init, prefs, or send_sms."""
    if sid in _linked:
        return True
    dest = calls.as_e164(to) or None
    sent = await calls.sms(sid, f"Your shortlist: {link}", to=dest)
    if sent:
        _linked.add(sid)
    return sent


def _as_list(val) -> list[str]:
    """ElevenLabs dashboard body fields are strings; accept a list or CSV."""
    if val is None or val == "":
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    return [p.strip() for p in str(val).split(",") if p.strip()]


def _as_text(val) -> str:
    """One spoken-length string. Lists collapse to a comma phrase."""
    if val is None or val == "":
        return ""
    if isinstance(val, list):
        return ", ".join(str(x).strip() for x in val if str(x).strip())
    return str(val).strip()


def _bind_renter_conv(sid: str, payload: dict) -> str:
    """Attach the inbound ElevenLabs conversation to this session if present."""
    cid = _nested_get(payload, "conversation_id", "system__conversation_id")
    bound = calls.bind_renter_conversation(sid, cid) if cid else ""
    if cid and not bound:
        log.info("renter conv not bound session=%s raw=%s", sid, cid[:24])
    return bound


@app.post("/agent/init")
async def agent_init(request: Request):
    """ElevenLabs calls this the moment an INBOUND call connects.

    An inbound call arrives cold - no client data - so {{session_id}} is empty
    and every webhook tool would otherwise mint its own session: preferences
    land in one, start_calls in another, and the page watches a third. We mint
    one here and hand it back as a dynamic variable for the whole call.

    It is also the only place we learn the caller's number, which is where the
    shortlist SMS has to go.
    """
    payload = await _request_payload(request)
    sid = secrets.token_urlsafe(6)
    caller = _apply_caller(payload)
    called = _nested_get(payload, "called_number", "to_number", "agent_number")

    def write(s):
        if caller:
            s.caller_phone = caller

    await store.mutate(sid, write)
    if not _bind_renter_conv(sid, payload):
        log.info("inbound session %s · no renter conversation_id", sid)
    link = f"{WEB_URL}/s/{sid}"
    log.info("inbound session %s · caller=%s · called=%s · keys=%s",
             sid, caller or "?", called or "?", sorted(payload.keys()))
    # Background: this webhook must return before the greeting. Pass `to`
    # explicitly so the send does not depend on a later store read.
    if caller:
        asyncio.create_task(_sms_link_once(sid, link, to=caller))
    monitor.record(sid, "renter", "init", "ok",
                   conversation_id=calls.renter_conversation(sid))

    # ElevenLabs merges these into the agent's dynamic variables for the call.
    return {
        "type": "conversation_initiation_client_data",
        "dynamic_variables": {
            "session_id": sid,
            "caller_phone": caller,
            "shortlist_url": link,
        },
    }


@app.post("/agent/preferences")
async def agent_preferences(payload: dict):
    """Caller described what they want, or reprioritized. Re-rank, speak one line."""
    sid = _ensure_session(payload)
    _bind_renter_conv(sid, payload)
    first = store.get(sid) is None
    fields = {k: v for k, v in payload.items() if k in Preferences.model_fields and v is not None}
    for key in ("areas", "priority_order", "extra_questions"):
        if key in fields:
            fields[key] = _as_list(fields[key])
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

    # Backup if pickup SMS has not gone out yet. Send even with an empty
    # shortlist — the page fills in as they talk.
    await _sms_link_once(sid, f"{WEB_URL}/s/{sid}", to=phone)
    # The model needs the ids to pass back to start_calls. They are never
    # spoken - `speak` is the only field that reaches the caller's ear - but
    # without them the model invents labels like "Listing 2" and nothing matches.
    shortlist = [
        {"listing_id": st.listing_id,
         "address": (L.by_id(st.listing_id).address if L.by_id(st.listing_id) else "")}
        for st in s.listings
    ]
    monitor.record(sid, "renter", "preferences", "ok",
                   summary=f"{n} listings",
                   conversation_id=calls.renter_conversation(sid))
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
        dest = calls.as_e164(token)
        if dest:
            # "call +111111111111" means: ring that number as the listing agent
            # for this shortlist, not a listing id.
            calls.set_session_dest(session_id, dest)
            continue
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


async def _ensure_call_targets(sid: str, ids: list[str]) -> list[str]:
    """Always have at least one listing to dial. Empty ids is why 'call them' no-ops."""
    s = store.get(sid)
    if not ids:
        ids = [st.listing_id for st in (s.listings if s else [])]
    if not ids:
        pool = L.load()
        ids = [pool[0].listing_id] if pool else []
    have = {st.listing_id for st in (s.listings if s else [])}

    def write(st):
        n = len(st.listings)
        for lid in ids:
            if lid in have or not L.by_id(lid):
                continue
            n += 1
            st.listings.append(ListingState(listing_id=lid, rank=n))
            have.add(lid)

    if any(lid not in have and L.by_id(lid) for lid in ids):
        await store.mutate(sid, write)
    return [lid for lid in ids if L.by_id(lid)]


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
    """Verify shortlist listings. One ring per DEMO_AGENT_PHONE, then stop."""
    sid = _ensure_session(payload)
    _bind_renter_conv(sid, payload)
    ids = await _ensure_call_targets(
        sid, _resolve_ids(_as_list(payload.get("listing_ids")), sid)
    )
    ids = calls.assign_demo_targets(sid, ids)
    extra = _as_list(payload.get("extra_questions"))
    availability = _as_text(payload.get("availability"))
    phone = _apply_caller(payload)

    if not ids:
        spoken = "I don't have a listing to call yet. Tell me what you're after first."
        await store.mutate(sid, lambda s: setattr(s, "agent_says", spoken))
        return {"speak": spoken, "session_id": sid, "called": 0}

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

    dests = [calls.destination(sid, L.by_id(lid)) for lid in ids]
    n = len(ids)
    spoken = (
        "Calling the listing agents now - watch your screen."
        if n > 1 else
        "Calling the listing agent now - watch your screen."
    )
    await store.mutate(sid, write)
    await store.mutate(sid, lambda s: setattr(s, "agent_says", spoken))
    log.info("start-calls[%s]: dial %s → %s", sid, ids, dests)
    monitor.record(sid, "renter", "start_calls", "started",
                   summary=",".join(ids),
                   conversation_id=calls.renter_conversation(sid))
    await calls.fan_out(sid, ids, extra, availability)
    monitor.record(sid, "renter", "start_calls", "done",
                   summary=f"called {n}",
                   conversation_id=calls.renter_conversation(sid))
    s = store.get(sid)
    if s and s.agent_says:
        spoken = s.agent_says
    return {"speak": spoken, "session_id": sid, "called": n, "to": dests}


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

    raw = {k: v for k, v in payload.items()
           if k in CallOutcome.model_fields and v is not None}
    if "addons" in raw:
        raw["addons"] = _as_list(raw["addons"])
    if isinstance(raw.get("answers"), str):
        raw["answers"] = {"notes": raw["answers"]}
    oc = CallOutcome(**raw)

    def write(st_):
        for st in st_.listings:
            if st.listing_id == lid:
                L.apply_outcome(st, oc)

    async with _outcome_lock:
        await store.mutate(sid, write)
        s = await rerank(sid)
    asyncio.create_task(calls.notify_renter(sid, lid))
    monitor.record(sid, "listing", "outcome", "ok",
                   summary=lid, listing_id=lid)
    return {"speak": "Got it, thanks.", "session_id": sid, "agent_says": s.agent_says}


def _book_decision(payload: dict) -> str:
    raw = _as_text(payload.get("decision") or payload.get("action") or "confirm").lower()
    if raw in {"reject", "rejected", "decline", "declined", "pass", "no"}:
        return "reject"
    return "confirm"


@app.post("/agent/book")
async def agent_book(payload: dict):
    """Plain code does the write - the model only calls this.

    Texts the renter and the listing-agent / landlord. decision=reject
    tells the landlord the renter is passing; it does not book.
    """
    sid = _ensure_session(payload)
    lid = _resolve_listing_id(payload, sid)
    slot = _as_text(payload.get("slot"))
    decision = _book_decision(payload)
    lst = L.by_id(lid)
    where = lst.address.split(",")[0] if lst else "it"
    if not lid:
        return {"speak": "Which listing was that?", "session_id": sid}

    if not slot:
        s = store.get(sid)
        card = next((st for st in (s.listings if s else []) if st.listing_id == lid), None)
        if card and card.outcome and card.outcome.viewing_slot:
            slot = card.outcome.viewing_slot

    if decision == "reject":
        spoken = f"I'll text the listing agent that we're passing on {where}."

        def write_pass(s):
            s.agent_says = spoken

        await store.mutate(sid, write_pass)
        when = f", {slot}" if slot else ""
        landlord = await calls.sms_landlord(
            sid, lid, f"The renter is not proceeding with {where}{when}.")
        monitor.record(sid, "renter", "book", "ok",
                       summary=f"reject {lid}", listing_id=lid,
                       conversation_id=calls.renter_conversation(sid))
        return {"speak": spoken, "session_id": sid, "decision": "reject",
                "landlord_sms": landlord}

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
    landlord = await calls.sms_landlord(
        sid, lid, f"Confirmed viewing: {where}, {slot}. The renter is coming.")
    monitor.record(sid, "renter", "book", "ok",
                   summary=f"confirm {lid}", listing_id=lid,
                   conversation_id=calls.renter_conversation(sid))
    return {"speak": spoken, "session_id": sid, "decision": "confirm",
            "landlord_sms": landlord}


@app.post("/agent/sms")
async def agent_sms(payload: dict):
    """Text the shortlist link. The model only calls this; Twilio sends it."""
    sid = _ensure_session(payload)
    _bind_renter_conv(sid, payload)
    phone = _apply_caller(payload)
    link = f"{WEB_URL}/s/{sid}"

    def write(s):
        if phone and not s.caller_phone:
            s.caller_phone = phone

    await store.mutate(sid, write)
    sent = await _sms_link_once(sid, link, to=phone)
    spoken = ("I've texted you the link. Have a look while we talk."
              if sent else
              "I couldn't text that number. What's a good mobile, with country code?")
    await store.mutate(sid, lambda s_: setattr(s_, "agent_says", spoken))
    monitor.record(sid, "renter", "sms", "ok" if sent else "failed",
                   conversation_id=calls.renter_conversation(sid))
    return {"speak": spoken, "session_id": sid, "sent": sent, "link": link}


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
