"""Twilio Media Streams <-> OpenAI Realtime, mounted on the main app.

Lifted from scripts/spike_bridge.py, which was written and proven before the
event. The three things that break are already solved there and unchanged here:

  1. Audio format - Twilio speaks base64 G.711 mu-law at 8kHz, BOTH directions.
  2. Barge-in - clear Twilio's queued audio AND truncate the assistant item.
  3. streamSid - arrives on the "start" frame, required on every frame back.

What is new today is tool dispatch: the model emits function_call_arguments.done
and we call the matching Python function IN-PROCESS, so a spoken sentence writes
SessionState with no HTTP hop, one port and one tunnel.
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets

import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

import calls
import listings as L
import state as store

TOOLS = json.loads(open("agent/tools.json").read())["tools"]
RENTER_TOOLS = [t for t in TOOLS if t["name"] in ("record_preferences", "start_calls", "book_viewing", "send_sms")]
LISTING_TOOLS = [t for t in TOOLS if t["name"] == "record_outcome"]

RENTER_PROMPT = (
    "You are an AI assistant that finds rentals in Toronto and calls listing agents "
    "on the caller's behalf. Open with: 'Hi, I'm an AI assistant that finds rentals in "
    "Toronto and calls the listing agents for you. I'll text you a live shortlist "
    "link now. What are you after?' "
    "Call send_sms immediately at the start of the call, before waiting for "
    "preferences, so they get the shortlist page. If it fails, ask for a mobile "
    "with country code and call send_sms again. "
    "Call record_preferences the moment they describe what they want, and AGAIN every "
    "time they change or reprioritise anything - do not wait for the end. "
    "Once they have a shortlist, or they ask you to call a listing agent, "
    "ALWAYS ask when they are free for viewings, then 'anything else you want me to ask?', "
    "then call start_calls with availability as one short string of those times. "
    "The moment you call start_calls, say exactly: "
    "'Wait until I gather all the information from the real estate agents.' "
    "Then stay silent. Do not chat, fill time, guess results, or pretend you called. "
    "start_calls can take a minute. If they talk while you wait, ask them to hold. "
    "When start_calls returns, read the speak field aloud. "
    "Be brief and natural. Never read JSON or listing ids aloud."
)


def listing_prompt(address: str, rent: int, extra: list[str], availability: str = "") -> str:
    asks = " Also ask: " + "; ".join(extra) if extra else ""
    when = (availability or "").strip()
    slot = (
        f"The renter is free {when}. Confirm those times with the landlord or listing "
        "agent and lock a viewing that fits. If none of those work, get the next open slot."
        if when else
        "Then ask for a viewing slot."
    )
    return (
        "You are an AI assistant calling a listing agent on behalf of a client. "
        "Identify yourself as an AI in your FIRST sentence, always. "
        f"You are asking about {address}, listed at ${rent:,} a month. "
        "Ask whether the unit is still available, what parking actually costs on top of "
        f"the listed rent, and the pet policy.{asks} {slot} "
        "Call record_outcome before you hang up with exactly what they told you and "
        "nothing they didn't. Keep it under 60 seconds and be polite."
    )


async def dispatch(name: str, args: dict, session_id: str, listing_id: str = "") -> str:
    """Tool call -> our own endpoints, in-process. The return is SPOKEN ALOUD:
    under 25 words, written as speech."""
    import main

    if name == "send_sms":
        r = await main.agent_sms({"session_id": session_id, **args})
        return r["speak"]
    if name == "record_preferences":
        r = await main.agent_preferences({"session_id": session_id, **args})
        return r["speak"]
    if name == "start_calls":
        r = await main.agent_start_calls({"session_id": session_id, **args})
        return r["speak"]
    if name == "book_viewing":
        r = await main.agent_book({"session_id": session_id, **args})
        return r["speak"]
    if name == "record_outcome":
        answers = args.pop("answers", None)
        if isinstance(answers, str):
            args["answers"] = {"extra": answers}
        await main.agent_outcome({"session_id": session_id, "listing_id": listing_id, **args})
        return "Thanks, that's really helpful. Have a good one."
    return "Sorry, I didn't catch that."


def attach(app: FastAPI) -> None:
    public = os.getenv("PUBLIC_URL", "").rstrip("/")
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")

    @app.api_route("/twiml/{role}", methods=["GET", "POST"])
    async def twiml(role: str, request: Request):
        """Twilio fetches this when the call connects; we hand it a websocket.
        Query params ride through so three concurrent calls never cross wires."""
        qs = str(request.url.query)
        sid = request.query_params.get("session")
        if role == "renter" and not sid:
            # Inbound: mint the session here so the SMS link exists immediately.
            sid = secrets.token_urlsafe(6)
            form = await request.form() if request.method == "POST" else {}
            caller = form.get("From", "") if form else ""
            await store.mutate(sid, lambda s: setattr(s, "caller_phone", caller))
            qs = f"session={sid}"
        ws = public.replace("https://", "wss://").replace("http://", "ws://")
        return HTMLResponse(
            f'<?xml version="1.0" encoding="UTF-8"?><Response>'
            f'<Connect><Stream url="{ws}/media/{role}?{qs}" /></Connect>'
            f"</Response>",
            media_type="application/xml",
        )

    @app.websocket("/media/{role}")
    async def media(twilio_ws: WebSocket, role: str):
        await twilio_ws.accept()
        q = twilio_ws.query_params
        session_id = q.get("session", "demo")
        listing_id = q.get("listing", "")
        extra = [e for e in q.get("extra", "").split("|") if e]
        availability = (q.get("avail") or "").replace("%20", " ")

        if role == "listing":
            lst = L.by_id(listing_id)
            prompt = listing_prompt(lst.address, lst.rent, extra, availability) if lst else RENTER_PROMPT
            tools = LISTING_TOOLS
        else:
            prompt, tools = RENTER_PROMPT, RENTER_TOOLS

        stream_sid: str | None = None
        last_item: str | None = None
        transcript: list[str] = []

        async with websockets.connect(
            f"wss://api.openai.com/v1/realtime?model={model}",
            additional_headers={"Authorization": f"Bearer {api_key}",
                                "OpenAI-Beta": "realtime=v1"},
        ) as ai:
            await ai.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["audio", "text"],
                    "instructions": prompt,
                    # (1) Twilio speaks G.711 mu-law. Both directions. Non-negotiable.
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "turn_detection": {"type": "server_vad"},
                    "input_audio_transcription": {"model": "whisper-1"},
                    "tools": tools,
                    "tool_choice": "auto",
                },
            }))
            # The agent speaks first, before the human says anything.
            await ai.send(json.dumps({"type": "response.create"}))

            async def twilio_to_openai():
                nonlocal stream_sid
                try:
                    while True:
                        frame = json.loads(await twilio_ws.receive_text())
                        if frame["event"] == "start":
                            # (3) Needed on every frame we send back.
                            stream_sid = frame["start"]["streamSid"]
                            print(f"  stream {stream_sid} [{role}/{session_id}]")
                        elif frame["event"] == "media":
                            await ai.send(json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": frame["media"]["payload"],
                            }))
                        elif frame["event"] == "stop":
                            break
                except WebSocketDisconnect:
                    pass

            async def openai_to_twilio():
                nonlocal last_item
                async for raw in ai:
                    ev = json.loads(raw)
                    kind = ev.get("type")

                    if kind == "response.audio.delta" and stream_sid:
                        await twilio_ws.send_json({
                            "event": "media", "streamSid": stream_sid,
                            "media": {"payload": ev["delta"]},
                        })
                    elif kind == "response.output_item.added":
                        last_item = ev.get("item", {}).get("id")

                    # (2) Barge-in. Drop what Twilio has buffered and truncate the
                    # assistant's turn, or it keeps talking over the interruption.
                    elif kind == "input_audio_buffer.speech_started":
                        if stream_sid:
                            await twilio_ws.send_json({"event": "clear", "streamSid": stream_sid})
                        if last_item:
                            await ai.send(json.dumps({
                                "type": "conversation.item.truncate",
                                "item_id": last_item, "content_index": 0, "audio_end_ms": 0,
                            }))
                            last_item = None

                    # Tools, in-process. No HTTP hop, no dashboard, no URLs to sync.
                    elif kind == "response.function_call_arguments.done":
                        name = ev.get("name", "")
                        args = json.loads(ev.get("arguments") or "{}")
                        print(f"  tool {name}({args}) [{session_id}]")
                        try:
                            out = await dispatch(name, args, session_id, listing_id)
                        except Exception as exc:
                            print(f"  ! tool {name} failed: {exc}")
                            out = "Let me note that down."
                        await ai.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {"type": "function_call_output",
                                     "call_id": ev["call_id"], "output": out},
                        }))
                        await ai.send(json.dumps({"type": "response.create"}))

                    elif kind == "conversation.item.input_audio_transcription.completed":
                        line = ev.get("transcript", "").strip()
                        transcript.append(f"them: {line}")
                        print(f"  caller: {line}")
                    elif kind == "response.audio_transcript.done":
                        transcript.append(f"us: {ev.get('transcript','').strip()}")
                    elif kind == "error":
                        print(f"  ! {ev.get('error')}")

            try:
                await asyncio.gather(twilio_to_openai(), openai_to_twilio())
            finally:
                # Safety net: if the listing agent hung up before record_outcome
                # fired, pull the facts out of the transcript rather than lose them.
                if role == "listing" and listing_id:
                    s = store.get(session_id)
                    st = next((x for x in (s.listings if s else []) if x.listing_id == listing_id), None)
                    if st and st.outcome is None:
                        oc = await calls.extract_outcome("\n".join(transcript), extra)
                        import main
                        await main.agent_outcome({"session_id": session_id,
                                                  "listing_id": listing_id,
                                                  **oc.model_dump()})
