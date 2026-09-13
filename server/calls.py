"""Outbound calls, SMS, CallOutcome extraction, email fallback.

Read .claude/skills/voice-calls/ first.
DO NOT build an audio pipeline. bridge.py owns audio entirely.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime

from openai import AsyncOpenAI

import listings as L
import state as store
import transport
from schemas import CallOutcome, CallStatus

log = logging.getLogger("realest.calls")

BUSINESS_HOURS = (9, 19)  # local; outside this the agent declines and offers email
CALL_TIMEOUT = 120        # listing-agent call + extract; start_calls waits this out
SMS_LINK_DELAY_S = 5      # SITE COBRA's trick: link lands while the caller is still talking
SMS_DEDUPE_WINDOW_S = 30  # same (to, body) fired twice within this window -> only sent once

OUT_OF_HOURS = (
    "It's outside business hours - I'd rather not cold-call them now. "
    "I've drafted emails instead and I'll text you when they reply."
)

E164 = re.compile(r"^\+[1-9]\d{7,14}$")

# session_id -> listing-agent number the caller asked us to dial
_session_dest: dict[str, str] = {}
# (session_id, listing_id) -> dest from DEMO_AGENT_PHONE[i]
_listing_dest: dict[tuple[str, str], str] = {}


def as_e164(raw: str) -> str:
    """Accept +14165550101, 4165550101, or +4165550101 (NANP missing the 1)."""
    if not raw:
        return ""
    raw = str(raw).strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        cand = "+" + digits
    elif len(digits) == 10 and digits[0] in "23456789":
        cand = "+1" + digits
    elif E164.match(raw):
        return raw
    else:
        return ""
    return cand if E164.match(cand) else ""


def demo_phones() -> list[str]:
    """DEMO_AGENT_PHONE as a CSV or JSON array of E.164 numbers."""
    raw = (os.getenv("DEMO_AGENT_PHONE") or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            items = []
    else:
        items = [p for p in re.split(r"[,;]+", raw) if p.strip()]
    out: list[str] = []
    for item in items:
        dest = as_e164(str(item))
        if dest:
            out.append(dest)
    return out


def set_session_dest(session_id: str, phone: str) -> str:
    """Remember which number this session should ring for listing-agent calls."""
    dest = as_e164(phone)
    if dest:
        _session_dest[session_id] = dest
    return dest


def destination(session_id: str, listing) -> str:
    """Where this listing's agent call actually goes.

    Per-listing demo pair first, then a caller-stated session dest, then the
    listing's own teammate number, then the first DEMO_AGENT_PHONE.
    """
    lid = getattr(listing, "listing_id", "") or ""
    if lid and (session_id, lid) in _listing_dest:
        return _listing_dest[(session_id, lid)]
    if session_id in _session_dest:
        return _session_dest[session_id]
    if listing and listing.agent_phone:
        return as_e164(listing.agent_phone) or listing.agent_phone
    phones = demo_phones()
    return phones[0] if phones else ""


def assign_demo_targets(session_id: str, listing_ids: list[str]) -> list[str]:
    """Zip shortlist onto DEMO_AGENT_PHONE. Stop when the phone list ends."""
    phones = demo_phones()
    if not phones:
        log.info("start-calls[%s]: no DEMO_AGENT_PHONE — not dialing", session_id)
        return []
    paired: list[str] = []
    for lid, phone in zip(listing_ids, phones):
        _listing_dest[(session_id, lid)] = phone
        paired.append(lid)
        log.info("start-calls[%s]: %s → %s", session_id, lid, phone)
    skipped = listing_ids[len(phones):]
    if skipped:
        log.info("start-calls[%s]: skip %s — demo numbers exhausted (%d)",
                 session_id, skipped, len(phones))
    return paired


def unique_destinations(session_id: str, listing_ids: list[str]) -> list[str]:
    """One live ring per number. Prefer assign_demo_targets for the demo path."""
    if transport.is_stub():
        return listing_ids
    seen: set[str] = set()
    out: list[str] = []
    for lid in listing_ids:
        lst = L.by_id(lid)
        dest = destination(session_id, lst)
        if dest and dest in seen:
            log.info("fan_out[%s]: skip %s — already calling %s", session_id, lid, dest)
            continue
        if dest:
            seen.add(dest)
        out.append(lid)
    return out

_ended: dict[str, bool] = {}           # session_id -> the call has already ended
_link_sms_started: set[str] = set()    # session_id -> the 5s link-SMS timer already ran once
_recent_sms: dict[tuple[str, str], float] = {}  # (to, body) -> last-sent monotonic time
_conversations: dict[tuple[str, str], str] = {}  # (session, listing) -> ElevenLabs conversation_id
_renter_conversation: dict[str, str] = {}        # session_id -> inbound renter conversation_id

POLL_EVERY_S = 5


def bind_renter_conversation(session_id: str, conversation_id: str) -> str:
    """Remember the inbound renter ConvAI id so outcomes can inject context."""
    cid = (conversation_id or "").strip()
    if not session_id or not cid.startswith("conv_"):
        return ""
    _renter_conversation[session_id] = cid
    log.info("renter conv bound session=%s conv=%s", session_id, cid)
    return cid


def renter_conversation(session_id: str) -> str:
    return _renter_conversation.get(session_id, "")


def _renter_update_line(session_id: str, listing_id: str) -> str:
    """One spoken-length fact for the live renter model. Not the raw transcript."""
    lst = L.by_id(listing_id)
    where = lst.address.split(",")[0] if lst else listing_id
    card = _listing_card(session_id, listing_id)
    if card is None:
        return ""
    if card.status is CallStatus.NO_ANSWER:
        line = f"{where}: no answer."
    elif card.status is CallStatus.DEAD:
        line = f"{where} is gone - already leased."
    elif card.outcome and card.outcome.viewing_slot:
        line = f"{where} is available, {card.outcome.viewing_slot}."
    elif card.outcome and card.outcome.available is False:
        line = f"{where} is gone."
    elif card.outcome and card.outcome.available is True:
        line = f"{where} is still available."
    else:
        line = f"{where}: listing call finished."
    return (
        f"Listing call result: {line} "
        "Tell the renter this when start_calls returns."
    )


async def notify_renter(session_id: str, listing_id: str) -> bool:
    """Push one listing outcome into the live renter conversation. Never raises."""
    cid = renter_conversation(session_id)
    if not cid:
        log.info("notify_renter[%s]: no renter conversation bound — skip", session_id)
        return False
    text = _renter_update_line(session_id, listing_id)
    if not text:
        return False
    try:
        import voice
        if not voice.is_elevenlabs():
            return False
        inject = getattr(voice.get_provider(), "inject_context", None)
        if not inject:
            return False
        ok = await inject(cid, text)
        log.info("notify_renter[%s/%s]: inject %s", session_id, listing_id,
                 "ok" if ok else "failed")
        return ok
    except Exception as exc:
        log.warning("notify_renter[%s/%s]: %s", session_id, listing_id, exc)
        return False


_TERMINAL = frozenset({"done", "failed", "completed", "error", "cancelled"})


def _twilio():
    from twilio.rest import Client
    sid, tok = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
    return Client(sid, tok) if sid and tok else None


def _openai() -> AsyncOpenAI | None:
    """Whichever provider has a key. Shared with server/chat.py so extraction
    works on OpenAI, OpenRouter or Gemini without a second code path."""
    import chat
    try:
        return chat._client()[0]
    except RuntimeError:
        return None


def within_business_hours(now: datetime | None = None) -> bool:
    """Outside hours the agent DECLINES to dial and says why - that is judgment
    about human norms, not a retry, and it belongs on camera."""
    if os.getenv("FORCE_BUSINESS_HOURS") == "1":
        return True
    h = (now or datetime.now()).hour
    return BUSINESS_HOURS[0] <= h < BUSINESS_HOURS[1]


async def place_call(
    session_id: str,
    listing_id: str,
    extra_questions: list[str],
    availability: str = "",
) -> str:
    """Place one outbound listing-agent call. Returns a provider call id.

    VOICE_PROVIDER=elevenlabs → one POST to ConvAI (dynamic vars carry session
    and listing). Otherwise Twilio Media Streams + /twiml/listing.
    """
    lst = L.by_id(listing_id)
    if lst is None:
        raise RuntimeError(f"listing {listing_id} not found")

    import voice
    if voice.is_elevenlabs():
        to = destination(session_id, lst)
        if not to:
            raise RuntimeError("no listing-agent number to dial")
        handle = await voice.get_provider().place_outbound(
            to_number=to,
            role="listing",
            dynamic_variables={
                "session_id": session_id,
                "listing_id": listing_id,
                "address": lst.address,
                "listing_address": lst.address,
                "listed_rent": str(lst.rent),
                "agent_name": lst.agent_name or "",
                "extra_questions": ", ".join(extra_questions),
                "availability": (availability or "").strip(),
            },
        )
        cid = handle.call_sid or handle.conversation_id or ""
        log.info("place_call[%s]: elevenlabs listing-agent %s → %s conv=%s sid=%s",
                 session_id, listing_id, to,
                 handle.conversation_id, handle.call_sid)
        if handle.conversation_id:
            _conversations[(session_id, listing_id)] = handle.conversation_id
            await watch_listing_call(
                session_id, listing_id, handle.conversation_id, extra_questions,
            )
        return cid

    client, public = _twilio(), os.getenv("PUBLIC_URL", "").rstrip("/")
    if client is None or not public:
        raise RuntimeError("twilio or listing not configured")

    q = f"session={session_id}&listing={listing_id}"
    if extra_questions:
        q += "&extra=" + "|".join(extra_questions).replace(" ", "%20")
    if availability:
        q += "&avail=" + str(availability).replace(" ", "%20")

    call = await asyncio.to_thread(
        client.calls.create,
        to=destination(session_id, lst),
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        url=f"{public}/twiml/listing?{q}",
    )
    return call.sid


async def fan_out(
    session_id: str,
    listing_ids: list[str],
    extra_questions: list[str],
    availability: str = "",
) -> list:
    """Three at once. Cards are already CALLING before we get here - that
    simultaneity is the shot. One failure must never kill the rest."""

    async def one(lid: str):
        try:
            if transport.is_stub():
                # A scripted listing agent answers. The transcript still goes
                # through the real extract_outcome() and the real re-rank -
                # only the dial tone is fake.
                transcript = await asyncio.wait_for(
                    transport.stub_call(lid, extra_questions), timeout=CALL_TIMEOUT
                )
                if transcript is None:
                    await mark_no_answer(session_id, lid, extra_questions)
                    return None
                oc = await extract_outcome(transcript, extra_questions)
                import main
                await main.agent_outcome({
                    "session_id": session_id, "listing_id": lid,
                    **oc.model_dump(mode="json"),
                })
                return lid
            # TRANSPORT=voice: real outbound on the Listing agent.
            # place_call() branches internally on voice.is_elevenlabs(): the
            # ElevenLabs leg fires the outbound call and schedules
            # watch_listing_call() as a background task, then returns
            # immediately - the outcome arrives later via that task or the
            # record_outcome webhook, not from this await. The Twilio leg is
            # unchanged. Either way, this call must stay fast so the card
            # flips to CALLING and doesn't spin.
            return await asyncio.wait_for(
                place_call(session_id, lid, extra_questions, availability), timeout=CALL_TIMEOUT
            )
        except Exception as exc:
            await mark_no_answer(session_id, lid, extra_questions)
            return exc

    return await asyncio.gather(*(one(l) for l in listing_ids), return_exceptions=True)


def _listing_card(session_id: str, listing_id: str):
    s = store.get(session_id)
    return next((st for st in (s.listings if s else []) if st.listing_id == listing_id), None)


def flatten_transcript(data: dict) -> str:
    """ElevenLabs conversation payload → plain text. Empty turns dropped."""
    turns = data.get("transcript") or data.get("transcripts") or []
    if isinstance(turns, str):
        return turns.strip()
    lines: list[str] = []
    for t in turns:
        if not isinstance(t, dict):
            continue
        role = str(t.get("role") or t.get("speaker") or "").strip()
        msg = t.get("message") or t.get("text") or t.get("content") or ""
        if isinstance(msg, list):
            bits = []
            for part in msg:
                if isinstance(part, dict):
                    bits.append(str(part.get("text") or part.get("message") or ""))
                else:
                    bits.append(str(part))
            msg = " ".join(bits)
        msg = str(msg).strip()
        if not msg:
            continue
        lines.append(f"{role}: {msg}" if role else msg)
    return "\n".join(lines)


def _conversation_status(data: dict) -> str:
    raw = data.get("status") or (data.get("metadata") or {}).get("status") or ""
    return str(raw).strip().lower()


async def watch_listing_call(
    session_id: str,
    listing_id: str,
    conversation_id: str,
    extra_questions: list[str],
) -> None:
    """Poll ConvAI until the listing call ends, then write the outcome.

    start_calls waits on this so the renter hears the result, not a dead 'calling'.
    """
    import voice
    provider = voice.ElevenLabsProvider()
    deadline = time.monotonic() + CALL_TIMEOUT
    last: dict = {}

    while time.monotonic() < deadline:
        card = _listing_card(session_id, listing_id)
        if card is not None and (card.outcome is not None or card.status is not CallStatus.CALLING):
            log.info("watch[%s/%s]: webhook already landed — stop", session_id, listing_id)
            return
        try:
            last = await provider.get_conversation(conversation_id)
        except Exception as exc:
            log.warning("watch[%s/%s]: poll failed: %s", session_id, listing_id, exc)
            await asyncio.sleep(POLL_EVERY_S)
            continue

        status = _conversation_status(last)
        text = flatten_transcript(last)
        if status in _TERMINAL:
            if text.strip():
                oc = await extract_outcome(text, extra_questions)
                import main
                await main.agent_outcome({
                    "session_id": session_id, "listing_id": listing_id,
                    **oc.model_dump(mode="json"),
                })
            else:
                why = (last.get("metadata") or {}).get("termination_reason") or status
                log.warning("watch[%s/%s]: empty transcript (%s) — %s",
                            session_id, listing_id, status, why)
                await mark_no_answer(session_id, listing_id, extra_questions)
            return
        await asyncio.sleep(POLL_EVERY_S)

    card = _listing_card(session_id, listing_id)
    if card is None or card.outcome is not None or card.status is not CallStatus.CALLING:
        return
    text = flatten_transcript(last)
    if text.strip():
        oc = await extract_outcome(text, extra_questions)
        import main
        await main.agent_outcome({
            "session_id": session_id, "listing_id": listing_id,
            **oc.model_dump(mode="json"),
        })
        return
    log.info("watch[%s/%s]: timeout — no-answer", session_id, listing_id)
    await mark_no_answer(session_id, listing_id, extra_questions)


async def mark_no_answer(session_id: str, listing_id: str, extra_questions: list[str]) -> None:
    """Timeout or error -> NO_ANSWER -> draft the email. Never leave it spinning."""
    draft = await draft_email(listing_id, extra_questions)

    def write(s):
        for st in s.listings:
            if st.listing_id == listing_id and st.status in (
                    CallStatus.CALLING, CallStatus.PENDING):
                st.status = CallStatus.NO_ANSWER
                st.email_draft = draft

    await store.mutate(session_id, write)
    asyncio.create_task(notify_renter(session_id, listing_id))


async def extract_outcome(transcript: str, extra_questions: list[str]) -> CallOutcome:
    """Transcript -> CallOutcome via OpenAI structured outputs.

    Never invent a field the human didn't say. A hallucinated value here
    destroys the claim the entire submission rests on.
    """
    client = _openai()

    def _degraded() -> CallOutcome:
        # No key, nothing to parse, or the API call itself failed: still never
        # leave `source` empty - 2.1's own acceptance criterion is "source
        # always set", not just "set when the model happens to cooperate".
        return CallOutcome(raw_transcript=transcript,
                           source=datetime.now().strftime("agent, %-I:%M%p").lower())

    if client is None or not transcript.strip():
        return _degraded()

    asked = "; ".join(extra_questions) or "none"
    try:
        import chat as _chat
        _, model = _chat._client()
        r = await client.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content":
                 "Extract ONLY what the listing agent actually said in this phone call. "
                 "If they did not mention something, leave it null - never guess. "
                 "If they said the unit is gone or already leased, set available=false. "
                 "real_rent = the listed rent PLUS every mandatory add-on they named. "
                 "addons = each mandatory extra cost as a short phrase that ALWAYS contains "
             "a numeric dollar figure, e.g. 'parking $180'. If they say an amount "
             "in words ('two hundred a month'), write it as digits ('parking $200'). "
             "The rent arithmetic downstream parses those digits. "
                 f"The caller also asked us to find out: {asked}. "
                 "Set `source` to who said it and when, e.g. 'Mark, 1:42pm'."},
                {"role": "user", "content": transcript},
            ],
            response_format=CallOutcome,
        )
    except Exception as exc:
        # A bad/expired/rate-limited key, or a provider that can't satisfy this
        # request shape, must degrade the same way a missing key does - never
        # crash the call that's landing this outcome.
        log.warning("extract_outcome: model call failed (%s) - falling back to raw transcript", exc)
        return _degraded()

    oc = r.choices[0].message.parsed or CallOutcome()
    oc.raw_transcript = transcript
    if not oc.source:
        oc.source = datetime.now().strftime("agent, %-I:%M%p").lower()
    return oc


async def draft_email(listing_id: str, extra_questions: list[str]) -> str:
    """Nobody answered, or it's the wrong hour. Draft it, show it on the card,
    one tap to send. Do not build SMTP plumbing."""
    lst = L.by_id(listing_id)
    if lst is None:
        return ""
    asks = ["Is the unit still available?",
            "What does parking actually cost on top of the listed rent?",
            "What's the pet policy?"] + list(extra_questions)
    body = "\n".join(f"- {a}" for a in asks)
    return (
        f"Subject: {lst.address} - still available?\n\n"
        f"Hi {lst.agent_name or 'there'},\n\n"
        f"I'm an AI assistant enquiring on behalf of a client about {lst.address} "
        f"(listed at ${lst.rent:,}). A few quick questions:\n\n{body}\n\n"
        "Happy to arrange a viewing this weekend if it's still open.\n\nThanks!"
    )


async def send_email(session_id: str, listing_id: str) -> bool:
    """Resend if configured; otherwise the draft stays on the card as evidence."""
    import httpx
    key = os.getenv("RESEND_API_KEY")
    s = store.get(session_id)
    st = next((x for x in (s.listings if s else []) if x.listing_id == listing_id), None)
    lst = L.by_id(listing_id)
    if not (key and st and st.email_draft and lst):
        return False
    subject, _, body = st.email_draft.partition("\n\n")
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post("https://api.resend.com/emails",
                         headers={"Authorization": f"Bearer {key}"},
                         json={"from": "Realest <onboarding@resend.dev>",
                               "to": [lst.agent_email], "subject": subject.replace("Subject: ", ""),
                               "text": body})
    return r.status_code < 300


def _sms_already_sent(to: str, body: str) -> bool:
    last = _recent_sms.get((to, body))
    return last is not None and time.monotonic() - last < SMS_DEDUPE_WINDOW_S


def _sms_remember(to: str, body: str) -> None:
    _recent_sms[(to, body)] = time.monotonic()


async def sms(session_id: str, body: str, to: str | None = None) -> bool:
    """One line. Long messages split into segments and arrive out of order.

    Validates the destination, de-dupes an identical send within a short
    window, retries once on a transient Twilio error, and never raises - a
    failed text must never take down the call flow around it."""
    session = store.get(session_id)
    if to is None or not str(to).strip():
        to = as_e164(session.caller_phone if session else "")
    else:
        to = as_e164(to)
    if not to:
        log.warning("sms[%s]: no valid E.164 destination - not sending", session_id)
        return False
    if session and not session.caller_phone:
        await store.mutate(session_id, lambda s: setattr(s, "caller_phone", to) if not s.caller_phone else None)

    if _sms_already_sent(to, body):
        log.info("sms[%s]: duplicate suppressed, already sent to %s within %ss",
                 session_id, to, SMS_DEDUPE_WINDOW_S)
        return True  # already delivered - not a failure

    client = _twilio()
    if client is None:
        log.warning("sms[%s]: Twilio not configured - not sending", session_id)
        return False

    from_number = as_e164(os.getenv("TWILIO_PHONE_NUMBER", "")) or os.getenv("TWILIO_PHONE_NUMBER")
    for attempt in (1, 2):
        try:
            await asyncio.to_thread(client.messages.create, body=body,
                                    from_=from_number, to=to)
            _sms_remember(to, body)
            log.info("sms[%s]: sent to %s (%d chars, attempt %d)", session_id, to, len(body), attempt)
            return True
        except Exception as exc:
            log.warning("sms[%s]: attempt %d failed: %s", session_id, attempt, exc)
            if attempt == 1:
                await asyncio.sleep(1)
    return False


async def sms_if_call_alive(session_id: str, link: str) -> None:
    """SITE COBRA sent the link 5s into the call, then cancelled if it had ended.
    The link lands while the caller is still talking - that's what makes the
    second screen feel like part of the conversation.

    Keyed by session_id, not a Twilio CallSid: session_id is already threaded
    through every part of the inbound call, so wiring this up from wherever
    the call actually starts needs no extra plumbing. Safe to call more than
    once for the same session - only the first schedules the timer."""
    if session_id in _link_sms_started:
        return
    _link_sms_started.add(session_id)

    await asyncio.sleep(SMS_LINK_DELAY_S)
    if _ended.get(session_id):
        log.info("sms_if_call_alive[%s]: call ended before %ss - not sending link",
                 session_id, SMS_LINK_DELAY_S)
        return
    await sms(session_id, f"Your shortlist: {link}")


def mark_call_ended(session_id: str) -> None:
    _ended[session_id] = True


async def email_all(session_id: str, listing_ids: list[str], extra_questions: list[str]) -> None:
    """Out of hours: draft for every selected listing, show them all on the page."""
    for lid in listing_ids:
        draft = await draft_email(lid, extra_questions)

        def write(s, lid=lid, draft=draft):
            for st in s.listings:
                if st.listing_id == lid:
                    st.status = CallStatus.NO_ANSWER
                    st.email_draft = draft

        await store.mutate(session_id, write)
