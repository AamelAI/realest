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

## 5 · Flip the switch (not yet)

When the spike works and you are ready to plumb outbound through the server:

```
VOICE_PROVIDER=elevenlabs
```

Until then the live path is still OpenAI Realtime (`make spike` / `make bridge` / `calls.place_call`).

---

## Checklist

| Env | Where it comes from |
|---|---|
| `ELEVENLABS_API_KEY` | Profile → API Keys |
| `ELEVENLABS_PHONE_NUMBER_ID` | Phone Numbers → imported Twilio number |
| `ELEVENLABS_RENTER_AGENT_ID` | Agents → renter |
| `ELEVENLABS_LISTING_AGENT_ID` | Agents → listing |
