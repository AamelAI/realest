"""Outbound calls, SMS, CallOutcome extraction, email fallback.

Read .claude/skills/voice-calls/ first.
DO NOT build an audio pipeline. bridge.py owns audio entirely.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime

from openai import AsyncOpenAI

import listings as L
import transport
import state as store
from schemas import CallOutcome, CallStatus

BUSINESS_HOURS = (9, 19)  # local; outside this the agent declines and offers email
CALL_TIMEOUT = 90         # never leave a card spinning

OUT_OF_HOURS = (
    "It's outside business hours - I'd rather not cold-call them now. "
    "I've drafted emails instead and I'll text you when they reply."
)

_ended: dict[str, bool] = {}


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


async def place_call(session_id: str, listing_id: str, extra_questions: list[str]) -> str:
    """One POST. Returns the Twilio call sid.

    session_id and listing_id ride the TwiML query string; they come back on the
    websocket and are how we know which card an outcome belongs to.
    """
    lst = L.by_id(listing_id)
    client, public = _twilio(), os.getenv("PUBLIC_URL", "").rstrip("/")
    if lst is None or client is None or not public:
        raise RuntimeError("twilio or listing not configured")

    q = f"session={session_id}&listing={listing_id}"
    if extra_questions:
        q += "&extra=" + "|".join(extra_questions).replace(" ", "%20")

    call = await asyncio.to_thread(
        client.calls.create,
        to=lst.agent_phone,
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        url=f"{public}/twiml/listing?{q}",
    )
    return call.sid


async def fan_out(session_id: str, listing_ids: list[str], extra_questions: list[str]) -> list:
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
            return await asyncio.wait_for(
                place_call(session_id, lid, extra_questions), timeout=CALL_TIMEOUT
            )
        except Exception as exc:
            await mark_no_answer(session_id, lid, extra_questions)
            return exc

    return await asyncio.gather(*(one(l) for l in listing_ids), return_exceptions=True)


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


async def extract_outcome(transcript: str, extra_questions: list[str]) -> CallOutcome:
    """Transcript -> CallOutcome via OpenAI structured outputs.

    Never invent a field the human didn't say. A hallucinated value here
    destroys the claim the entire submission rests on.
    """
    client = _openai()
    if client is None or not transcript.strip():
        return CallOutcome(raw_transcript=transcript)

    asked = "; ".join(extra_questions) or "none"
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
             "addons = each extra cost as a short phrase, e.g. 'parking $180'. "
             f"The caller also asked us to find out: {asked}. "
             "Set `source` to who said it and when, e.g. 'Mark, 1:42pm'."},
            {"role": "user", "content": transcript},
        ],
        response_format=CallOutcome,
    )
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


async def sms(session_id: str, body: str, to: str | None = None) -> bool:
    """One line. Long messages split into segments and arrive out of order."""
    client = _twilio()
    to = to or store.get(session_id).caller_phone if store.get(session_id) else None
    if client is None or not to:
        return False
    await asyncio.to_thread(client.messages.create, body=body,
                            from_=os.getenv("TWILIO_PHONE_NUMBER"), to=to)
    return True


async def sms_if_call_alive(session_id: str, call_sid: str, link: str) -> None:
    """SITE COBRA sent the link 5s into the call, then cancelled if it had ended.
    The link lands while the caller is still talking - that's what makes the
    second screen feel like part of the conversation."""
    await asyncio.sleep(5)
    if _ended.get(call_sid):
        return
    await sms(session_id, f"Your shortlist: {link}")


def mark_call_ended(call_sid: str) -> None:
    _ended[call_sid] = True


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
