# If the OpenAI Realtime API isn't available

Run `make keys` first. If it says **NO realtime model on this key**, read this. If realtime is available, ignore this file — the bridge works as designed.

## Why this happens

Hackathon credit grants are not all the same thing. **Codex credits authorize the coding agent, not the API.** A key that works beautifully for writing code can return `401` or `429` against `api.openai.com/v1/realtime`. Nothing is wrong with the key; it just isn't scoped to what we need.

Three ways out, cheapest first.

---

## Option A — Twilio's own speech, OpenRouter for the brain

**Zero extra accounts. Zero extra cost. No OpenAI dependency at all.**

Twilio can transcribe the caller and speak back without any model provider. The conversation becomes turn-based instead of continuous:

```xml
<Response>
  <Gather input="speech" speechTimeout="auto" action="/voice/turn" method="POST">
    <Say voice="Polly.Amy-Neural">
      Hi, I'm an AI assistant that finds rentals in Toronto and calls the
      listing agents for you. What are you after?
    </Say>
  </Gather>
</Response>
```

Twilio POSTs `SpeechResult` to `/voice/turn`. You send that text to OpenRouter, get a reply plus any tool call, and answer with more TwiML:

```python
@app.post("/voice/turn")
async def turn(SpeechResult: str = Form(""), CallSid: str = Form("")):
    reply, tool = await think(CallSid, SpeechResult)   # OpenRouter
    if tool:
        await dispatch(tool, CallSid)                  # same functions as the bridge
    return twiml_say_and_gather(reply)
```

**What you lose:** ~2–4s between turns instead of under a second, and no barge-in — the caller can't interrupt mid-sentence.

**What you keep:** everything that actually wins. Outbound calls to listing agents, `CallOutcome` extraction, the re-rank, the live page, the SMS. The differentiator is untouched.

**Say it in the README as a design note, not an apology:** *"Turn-based voice over Twilio ASR keeps the entire stack on sponsor infrastructure."* Judges score working systems, not latency benchmarks.

### Voices worth using
`Polly.Amy-Neural`, `Polly.Matthew-Neural`, `Polly.Joanna-Neural`. Set `<Say voice="…">` explicitly — the default Twilio voice sounds like 2011 and it will be in your video.

---

## Option B — a personal OpenAI key with a few dollars on it

Realtime audio for a day of rehearsal and one recorded demo is a few dollars, not tens. If someone on the team already has an API account with billing enabled, this is the fastest path back to the design as written: change one value in `.env` and everything else works unchanged.

**Set a hard usage limit first** (platform.openai.com → billing → limits). A websocket left open while you sleep is the only way this gets expensive.

---

## Option C — a managed voice provider's free tier

Vapi, Retell and ElevenLabs all have trial tiers that include a handful of telephony minutes. Enough for rehearsal plus a recorded take.

**Costs you the most time** — a new account, a new agent, a new webhook shape — so take it only if A and B are both closed.

---

## Which to pick, at 11:15

| Situation | Do this |
|---|---|
| `make keys` shows a realtime model | Nothing. The bridge already works |
| No realtime, someone has a billed OpenAI account | **Option B.** One env value, five minutes |
| No realtime, nobody has billing | **Option A.** Ships today, costs nothing, keeps the differentiator |
| A and B both closed | Option C, and accept the setup cost |

**Decide by 11:45 and say it out loud** — that's task `0.9`. Do not spend the morning trying to make a Codex key do something it was never scoped to do.

---

## What does not change

Whichever option you take, these are identical:

- Outbound calls to listing agents — the thing a chatbox cannot do
- `CallOutcome` extraction into a typed schema
- Re-ranking the shortlist from what a human said
- The live page, the SMS link, tap-to-confirm
- The email fallback and the hour-of-day check

The voice transport is an implementation detail. **The product is the phone call and the reshuffle.**
