---
name: voice-calls
description: Wiring the OpenAI Realtime voice agents over Twilio, placing outbound calls, defining function tools, and fanning out three calls at once. Use when working on server/calls.py, agent/tools.json, telephony setup, SMS, or anything involving the phone.
---

# Voice and calls

## Read this first

**The audio bridge already exists and is already proven — `scripts/spike_bridge.py`.** It handles the three things that break: G.711 μ-law format both directions, barge-in (clear Twilio's buffer *and* truncate the assistant item), and `streamSid` on every outgoing frame.

**Build on it. Do not rewrite it, and do not debug it during the build.** It was written and tested before the event precisely so that build-day time goes to the product instead of to audio.

Calls run on **OpenAI Realtime over Twilio Media Streams** — marquee sponsor, event credits, no third-party voice vendor and nothing out of pocket. Reference: Twilio's official Python samples for inbound and outbound.

## Placing an outbound call

Twilio dials; its TwiML points at our websocket; the bridge proxies audio to OpenAI.

```python
call = twilio.calls.create(
    to=listing.agent_phone,                    # E.164, always a teammate's number
    from_=TWILIO_PHONE_NUMBER,
    url=f"{PUBLIC_URL}/twiml/listing?session={session_id}&listing={listing.listing_id}",
)
```

**Carry `session_id` and `listing_id` in the TwiML query string.** Twilio passes them through to the websocket handler, and they are how you know which card an outcome belongs to. Get this wrong and three concurrent calls all write to one listing.

Per-call context (address, listed rent, the caller's extra questions) goes into the Realtime `session.update` instructions when that call's websocket opens — see `spike_bridge.py`.

## Three calls at once

```python
results = await asyncio.gather(
    *(place_call(session_id, lst) for lst in selected),
    return_exceptions=True,
)
```

- Flip each card to `CALLING` **before** awaiting, so the page shows all three going live at once. That simultaneity is the shot.
- `return_exceptions=True` — one provider error must not kill the other two.
- Wrap each call in `asyncio.wait_for(..., timeout=90)`. A call that never resolves hangs the demo.
- On timeout or exception → status `NO_ANSWER` → draft the email. Never leave a card spinning.

## Tools are in-process, not webhooks

Realtime function tools are declared in `session.update` when the call's websocket opens. The model emits `response.function_call_arguments.done`; the bridge calls the matching Python function **directly** and replies with a `function_call_output`. No HTTP hop, no dashboard, no URLs to keep in sync.

Definitions live in `agent/tools.json`. The **description field is the prompt** — it's what the model reads to decide when to fire. Write it like you're briefing a person.

```python
# in the bridge, on a function call
if ev["type"] == "response.function_call_arguments.done":
    result = await dispatch(ev["name"], json.loads(ev["arguments"]), session_id)
    await ai.send(json.dumps({
        "type": "conversation.item.create",
        "item": {"type": "function_call_output",
                 "call_id": ev["call_id"],
                 "output": result},        # spoken aloud — under 25 words, written as speech
    }))
    await ai.send(json.dumps({"type": "response.create"}))
```

Renter agent gets `record_preferences`, `start_calls`, `book_viewing`. Listing agent gets `record_outcome`. Don't give either the other's tools.

**The output string is spoken aloud.** Keep it short and write it as speech, never as a JSON summary.

## Two agents, two prompts

| Agent | Faces | Job |
|---|---|---|
| Renter agent | inbound caller | Elicit preferences, offer to verify, ask "anything else you want me to ask?", report back |
| Listing agent | outbound realtor | Identify itself as an AI in the first sentence, ask availability / real cost / pets / the caller's extra questions, propose a slot |

The outbound agent's opening line is non-negotiable: **it says it's an AI before it asks anything.** That's both the right thing and criterion-4 evidence.

## The SMS trick

SITE COBRA sent the link **5 seconds into the call**, then cancelled if the call had already ended. Steal it exactly — the link lands while the caller is still talking, which is what makes the second screen feel like part of the conversation instead of a follow-up.

```python
async def sms_if_call_alive(conversation_id, to_number, link):
    await asyncio.sleep(5)
    if ended_calls.get(conversation_id):
        return
    twilio.messages.create(body=f"Your shortlist: {link}", from_=NUMBER, to=to_number)
```

## Hour-of-day judgment

Before any outbound call, check local time. Outside roughly 9:00–19:00, **the agent declines and says why**:

> "It's after seven — I'd rather not cold-call them now. I can email all three tonight and text you when they reply, or try first thing Monday."

This is not a fallback, it's judgment about human norms, and almost no other submission will have it. Put it on camera.

## Extracting the outcome

The transcript is not the product — `CallOutcome` is. After each call, pull the transcript from the provider and run it through OpenAI structured outputs into the `CallOutcome` schema.

**Never invent a field the human didn't say.** If they didn't mention pets, `pets_allowed` is `None`. The entire pitch is that these facts came from a person; a hallucinated one destroys the claim.

Always populate `source` — `"Mark, 1:42pm"`. Provenance on the card turns the page from a UI into evidence.

## Setup checklist

Full runbook: [docs/VOICE_SPIKE.md](../../../docs/VOICE_SPIKE.md). In short:

1. ngrok free static domain → `PUBLIC_URL`
2. Twilio number (Voice **and** SMS), all three teammate phones added to **Verified Caller IDs**
3. `OPENAI_API_KEY` in `.env`
4. `make bridge` · `make tunnel` · `make spike TO=…`

**Done when** your phone rings, the agent speaks first, and it stops when you interrupt. Until that works, nothing else in this lane matters.

## Gotchas

- Three simultaneous outbound calls may need more than one Twilio number. Test concurrency early, not at 14:00.
- Use your ngrok **static** domain. A restarted tunnel with a new URL breaks every in-flight call.
- Every `agent_phone` in `data/listings.json` is a teammate's number. We never cold-call real people with a bot.
- Twilio trial accounts only dial **verified** numbers. Error `21219` means the destination isn't verified.
- Audio format, barge-in and `streamSid` are already solved in `spike_bridge.py`. If audio misbehaves, read it before changing it.
