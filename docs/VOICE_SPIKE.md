# Voice spike — the 20-minute runbook

The only irreversible risk left. Do this before sleeping, not in the morning.

**Success is one thing:** your own phone rings and an agent talks to you. Until that happens, nothing else in the telephony lane matters.

If it fails, you find out now — while there's still time to pivot to browser-mic input and keep the outbound leg, which is the half that actually wins. Finding out at 11:30 with three people watching is how a project dies.

---

## 1 · Twilio — number and verified phones · ~8 min

1. Sign up at [twilio.com](https://www.twilio.com/try-twilio), verify your own phone.
2. **Phone Numbers → Buy a number.** Filter **Canada**, area code **416** or **647**. Require **Voice** *and* **SMS** capability. A Toronto number calling Toronto listing agents looks right on camera.
3. **This is the step people miss:** a Twilio trial can only call *verified* numbers. Go to **Phone Numbers → Verified Caller IDs** and add all three teammate phones — every `agent_phone` in `data/listings.json` is one of them. Either verify them, or add ~$20 and upgrade out of trial.
4. Copy `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` into `.env`.

> **Failure here looks like:** call placed successfully, phone never rings. That's an unverified destination nine times out of ten.

---

## 2 · Voice provider — two agents · ~8 min

Any managed conversational-telephony provider works — ElevenLabs ConvAI, Vapi, Retell. The shape is identical: one POST with an agent id, a phone-number id and a destination. `scripts/spike_call.py` is written against ElevenLabs; swap the URL and payload keys for the others.

1. Create the account, grab the API key → `VOICE_API_KEY`.
2. **Import the Twilio number** on the provider side (it'll ask for the SID and auth token). Note the provider's own id for it → `VOICE_PHONE_NUMBER_ID`.
3. Create the **renter agent** → `VOICE_RENTER_AGENT_ID`. First line:

   > "Hi — I'm an AI assistant that finds rentals in Toronto and calls the listing agents for you. What are you after?"

4. Create the **listing agent** → `VOICE_LISTING_AGENT_ID`. It must identify itself as an AI in its first sentence — that's both the right thing and criterion-4 evidence:

   > "Hi, I'm an AI assistant calling on behalf of a client about the {{listing_address}} listing. Is it still available, and what does parking actually cost?"

Two agents, because they face opposite directions and want opposite prompts. Don't try to make one do both.

---

## 3 · Ring your own phone · ~2 min

```bash
make spike TO=+1416XXXXXXX
```

You want:

```
✓ call placed
  conversation  conv_abc123…
  call sid      CA…
```

…and then your phone ringing.

The script maps the common failures for you: `401/403` wrong key · `404` wrong agent or number id · `400` number not imported provider-side, or destination not verified on a trial.

After you hang up:

```bash
uv run python scripts/spike_call.py --to +1416XXXXXXX --status conv_abc123
```

That returns status and the full transcript — the same endpoint `calls.py` will poll during the build to get `CallOutcome` input.

---

## 4 · One webhook tool, end to end · ~2 min

Proves the agent can reach *your* code, which is the part everything else depends on.

```bash
make tunnel                                    # separate terminal
make tools URL=https://<your-domain>.ngrok.app # rewrites agent/tools.json
```

Register `record_preferences` from `agent/tools.json` in the provider dashboard, then call yourself and say *"two bedrooms in King West under thirty-four hundred."*

**Done when your FastAPI logs the tool call with its arguments.** That's the whole architecture proven: phone → provider → your server.

---

## If it doesn't work by 4am

Stop and go to bed. Bring the failure to the 11:15 gate and take the documented fallback — browser-mic Realtime for the inbound leg, keep the outbound calls. The outbound leg is the part worth saving; the inbound one is a convenience.

Do **not** burn two hours on audio debugging tonight. That's the trap this whole architecture was chosen to avoid.

---

## Afterwards

```bash
make doctor
```

Green means `.env` is complete and the tunnel URL is in `agent/tools.json`. Then sleep — the morning list is in `BACKLOG.md`.
