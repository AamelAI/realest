# Voice spike — the runbook

**Everything here is free.** OpenAI is the marquee sponsor and supplies builder credits; Twilio's trial credit covers a number and far more test calls than you'll make; ngrok gives every account one static domain on the free plan. No third-party voice vendor, nothing out of pocket.

The trade for that is ~80 lines of audio proxying, already written in `scripts/spike_bridge.py`. You pay it once, tonight, and never again.

**Success is one thing:** your own phone rings, an agent talks, and it stops when you interrupt. Until that happens, nothing else in the telephony lane matters.

---

## 1 · ngrok — free static domain · 2 min

```bash
ngrok config add-authtoken <token>
```

Claim your free static domain in the dashboard (**Domains → New Domain**). Every account gets one, and it's the whole point — Twilio and OpenAI both need a URL that survives a restart.

Put it in `.env` as `PUBLIC_URL=https://<your>.ngrok-free.app`, then:

```bash
make tunnel
```

---

## 2 · Twilio — number and verified phones · 8 min

1. Sign up at [twilio.com](https://www.twilio.com/try-twilio). The trial credit covers everything below.
2. **Phone Numbers → Buy a number.** Filter **Canada**, area code **416** or **647**, require **Voice** *and* **SMS**. A Toronto number calling Toronto listing agents looks right on camera.
3. **The step people miss:** a trial account can only call *verified* numbers. **Phone Numbers → Verified Caller IDs** → add all three teammate phones. Every `agent_phone` in your listings is one of them.
4. `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` into `.env`.

> **Failure here looks like:** call reports success, phone never rings. That's an unverified destination nine times out of ten — `spike_call.py` catches error `21219` and tells you.

---

## 3 · OpenAI · 1 min

`OPENAI_API_KEY` into `.env`. That's it — no agent to create, no number to import. The prompt lives in `spike_bridge.py` and you edit it in a text editor, not a dashboard.

Grab event credits at the 10:30 briefing if they're offered.

---

## 4 · Ring your own phone · 3 min

Three terminals:

```bash
make bridge                  # 1 — Twilio <-> OpenAI audio proxy
make tunnel                  # 2 — ngrok
make spike TO=+1416XXXXXXX   # 3 — place the call
```

You want:

```
  bridge ok · model gpt-realtime
✓ call placed · sid CA… · listing voice
```

…then your phone rings and the agent **speaks first**.

**Then interrupt it mid-sentence.** It must stop talking immediately. That's barge-in working, and it's the difference between a demo that feels real and one that sounds broken. Transcripts print live in the bridge terminal.

`make spike TO=… ROLE=renter` switches to the caller-facing voice.

---

## Why outbound, not inbound, first

OpenAI's SIP connector makes *inbound* calls very clean — point a Twilio SIP trunk at `sip:<project-id>@sip.api.openai.com` and you're done. But **outbound over SIP isn't documented**, and outbound is your differentiator.

Media Streams handles both directions, and Twilio publishes official Python samples for each. So: one mechanism, both legs, no undocumented paths on the thing that wins.

If you want the inbound leg cleaner later, the SIP route is a drop-in for that half. Don't touch it tonight.

---

## The three things that break

Already handled in `spike_bridge.py`, but know them so you can debug at 13:00:

1. **Audio format.** Twilio speaks base64 G.711 μ-law at 8kHz. Both `input_audio_format` and `output_audio_format` must be `g711_ulaw`. Mismatch gives silence or static and an hour of confusion.
2. **Barge-in.** On `input_audio_buffer.speech_started`, clear Twilio's queued audio *and* truncate the assistant item. Skip either and the agent talks over the interruption.
3. **`streamSid`.** Arrives on the `start` frame, required on every frame you send back. Miss it and audio silently goes nowhere.

---

## If it doesn't work by 4am

Stop and go to bed. Bring it to the 11:15 gate and take the fallback: browser-mic Realtime over WebRTC for the inbound leg, keep the outbound calls. **The outbound leg is the half that wins**; inbound is a convenience.

Do not burn two hours on audio debugging tonight.

---

## Afterwards

```bash
make doctor
```

Green means `.env` is complete and the tunnel is in `agent/tools.json`. Then sleep — the morning list is in [BACKLOG.md](../BACKLOG.md).
