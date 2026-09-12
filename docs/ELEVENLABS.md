# ElevenLabs — Phase 0 runbook

Managed conversational telephony. You never touch audio. The Python client is `server/voice/elevenlabs.py`; this page is the dashboard work only you can do.

Pick **ElevenAgents** at signup (not ElevenCreative). Creative is TTS/studio. Agents is phones, tools, outbound.

---

## 1 · Account and API key · 2 min

1. Sign up at [elevenlabs.io](https://elevenlabs.io) → **ElevenAgents**.
2. **Profile → API Keys** → create a key.
3. Put it in `.env` as `ELEVENLABS_API_KEY=…`

```bash
make keys
```

The ElevenLabs section should go green on the key. Agent/phone ids can still be yellow.

---

## 2 · Import the Twilio number · 5 min

Use the Twilio number you already have (`TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER`). Do not buy a second number.

1. ElevenLabs → **Phone Numbers** → import / connect Twilio.
2. Copy the phone-number id (not the E.164) into `ELEVENLABS_PHONE_NUMBER_ID`.

Trial Twilio still only dials **Verified Caller IDs**. Same restriction as `make spike`.

---

## 3 · Two agents · 10 min

Create two agents. Prompts only for Phase 0 — webhook tools are later (`agent/elevenlabs-tools.json`).

### Renter (inbound)

First message:

> Hi, I'm an AI assistant that finds rentals in Toronto and calls the listing agents for you. What are you after?

Assign the imported Twilio number to this agent so a human dial-in hits it. Copy the agent id → `ELEVENLABS_RENTER_AGENT_ID`.

### Listing (outbound)

First message **must** identify as an AI, then ask availability, real parking cost, pets, a viewing slot. Under 60 seconds.

Copy the agent id → `ELEVENLABS_LISTING_AGENT_ID`.

---

## 4 · Ring a phone

```bash
# leave VOICE_PROVIDER=openai_realtime until this rings
make eleven-spike TO=+1YOUR_VERIFIED_NUMBER
# or: make eleven-spike TO=+1… ROLE=renter
```

**Done when** your phone rings, the agent speaks, and it stops when you interrupt.

That command uses `ElevenLabsProvider` — the same class `calls.place_call()` will call later. It does not start `make bridge`.

---

## 5 · Phase 1 — plumb into the server

The spike only proves the vendor. Phase 1 is `start_calls` → `fan_out` → `place_call` → ElevenLabs, and dashboard tools hitting `/agent/*`.

In `.env`:

```
TRANSPORT=voice
VOICE_PROVIDER=elevenlabs
```

Leave `TRANSPORT=stub` if you only want scripted listing agents (no phone). Stub ignores `VOICE_PROVIDER`.

### Webhook tools

`make tunnel` must be up. Then:

```bash
make eleven-tools
```

That prints `agent/elevenlabs-tools.json` with `{PUBLIC_URL}` replaced. In ElevenLabs:

1. **Renter** agent → Tools → add `record_preferences`, `start_calls`, `book_viewing` as **webhook / POST**.
2. **Listing** agent → Tools → add `record_outcome` as **webhook / POST**.
3. For `session_id` and `listing_id`, use dynamic variables (`{{session_id}}`, `{{listing_id}}`). Do not let the model invent them.
4. Default method is GET — set **POST** or the body never arrives.

The server already implements those routes. The tool result is JSON; the agent should read the `speak` field aloud.

### Done when

1. `GET /health` shows `"transport":"voice","voice_provider":"elevenlabs"`.
2. A `POST /agent/start-calls` (or the renter saying “call Wellington”) rings a teammate as the listing agent.
3. That agent’s `record_outcome` webhook flips the card and re-ranks.

Inbound renter calls still work if the Twilio number is assigned to the Renter agent in the dashboard. Outbound listing calls no longer need `make bridge`.

---

## Checklist

| Env | Where it comes from |
|---|---|
| `ELEVENLABS_API_KEY` | Profile → API Keys |
| `ELEVENLABS_PHONE_NUMBER_ID` | Phone Numbers → imported Twilio number |
| `ELEVENLABS_RENTER_AGENT_ID` | Agents → renter |
| `ELEVENLABS_LISTING_AGENT_ID` | Agents → listing |
