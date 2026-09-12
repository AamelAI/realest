#!/usr/bin/env python3
"""Twilio Media Streams <-> OpenAI Realtime bridge. Connectivity spike.

    make bridge          # terminal 1
    make tunnel          # terminal 2
    make spike TO=+1416…  # terminal 3

Adapted from Twilio's official sample (twilio-samples/speech-assistant-openai-
realtime-api-python). This is transport plumbing and starter code, which the
eligibility rules explicitly allow. The product - preference extraction,
ranking, CallOutcome, the reshuffle - is built during the event in server/.

WHY THIS EXISTS
---------------
This file is the whole reason the voice layer is free. OpenAI is the marquee
sponsor and supplies builder credits; running audio through the Realtime API
means no third-party voice vendor and nothing out of pocket. The cost is ~80
lines of audio proxying, which you pay once, tonight, and never again.

THE THREE THINGS THAT BREAK
---------------------------
1. Audio format. Twilio speaks base64 G.711 mu-law at 8kHz. Set BOTH
   input_audio_format and output_audio_format to "g711_ulaw" or you get
   silence or static and an hour of confusion.
2. Barge-in. When the caller interrupts, you must clear Twilio's queued audio
   AND truncate the assistant item, or the agent talks over itself. Handled in
   `on_speech_started` below. This is the single most common demo killer.
3. streamSid. Arrives on the "start" frame, required on every frame you send
   back. Miss it and audio silently goes nowhere.
"""
from __future__ import annotations

import base64
import json
import os

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
REALTIME_WS = f"wss://api.openai.com/v1/realtime?model={MODEL}"

RENTER_PROMPT = (
    "You are an AI assistant that finds rentals in Toronto and calls listing agents "
    "on the caller's behalf. Open with: 'Hi, I'm an AI assistant that finds rentals in "
    "Toronto and calls the listing agents for you. What are you after?' "
    "Be brief and natural. Never read JSON aloud."
)
LISTING_PROMPT = (
    "You are an AI assistant calling a listing agent on behalf of a client. "
    "Identify yourself as an AI in your FIRST sentence, always. Ask whether the unit is "
    "still available, what parking actually costs on top of the listed rent, and the pet "
    "policy. Then ask for a viewing slot. Keep it under 60 seconds and be polite."
)

app = FastAPI(title="spike-bridge")


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL, "public_url": PUBLIC_URL}


@app.api_route("/twiml/{role}", methods=["GET", "POST"])
def twiml(role: str):
    """Twilio fetches this when the call connects, and we hand it a websocket."""
    ws = PUBLIC_URL.replace("https://", "wss://").replace("http://", "ws://")
    return HTMLResponse(
        f'<?xml version="1.0" encoding="UTF-8"?><Response>'
        f'<Connect><Stream url="{ws}/media/{role}" /></Connect>'
        f"</Response>",
        media_type="application/xml",
    )


@app.websocket("/media/{role}")
async def media(twilio_ws: WebSocket, role: str):
    await twilio_ws.accept()
    prompt = LISTING_PROMPT if role == "listing" else RENTER_PROMPT
    stream_sid: str | None = None
    last_item: str | None = None

    async with websockets.connect(
        REALTIME_WS,
        additional_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1",
        },
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
                        print(f"  stream {stream_sid} [{role}]")
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
                        "event": "media",
                        "streamSid": stream_sid,
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
                            "item_id": last_item,
                            "content_index": 0,
                            "audio_end_ms": 0,
                        }))
                        last_item = None

                elif kind == "conversation.item.input_audio_transcription.completed":
                    print(f"  caller: {ev.get('transcript', '').strip()}")
                elif kind == "error":
                    print(f"  ! {ev.get('error')}")

        import asyncio
        await asyncio.gather(twilio_to_openai(), openai_to_twilio())


if __name__ == "__main__":
    import uvicorn

    if not OPENAI_API_KEY:
        raise SystemExit("✗ OPENAI_API_KEY not set in .env")
    if not PUBLIC_URL:
        raise SystemExit("✗ PUBLIC_URL not set in .env (your ngrok static domain)")
    print(f"bridge on :8000 · model {MODEL} · public {PUBLIC_URL}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
