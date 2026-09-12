---
name: voice-calls
description: Wiring the managed voice agent, placing outbound calls, defining webhook tools, and fanning out three calls at once. Use when working on server/calls.py, agent/tools.json, telephony setup, SMS, or anything involving the phone.
---

# Voice and calls

## Read this first

**Do not build an audio pipeline.** No media-stream websockets, no μ-law encoding, no barge-in handling. A managed conversational-telephony provider owns all of that, and it is the single biggest time sink you can avoid today.

SITE COBRA took 3rd place at AI Tinkerers Poland with a telephony layer of **182 lines and one HTTP POST**. Their source is the reference implementation for this section: [`voicebotcall/main.py`](https://github.com/PiotrTyrakowski/DeepMindHackaton/blob/main/voicebotcall/main.py) and [`elevenlabs-tools.json`](https://github.com/PiotrTyrakowski/DeepMindHackaton/blob/main/elevenlabs-tools.json).

## Placing an outbound call

One POST. The provider dials, runs the conversation, and calls our webhooks when it needs something.

```python
payload = {
    "agent_id": AGENT_ID,
    "agent_phone_number_id": PHONE_NUMBER_ID,
    "to_number": listing.agent_phone,          # E.164, e.g. "+14165550123"
    "conversation_initiation_client_data": {
        "dynamic_variables": {
            "listing_address": listing.address,
            "listed_rent": str(listing.rent),
            "extra_questions": "; ".join(prefs.extra_questions),
            "session_id": session_id,           # so the outcome webhook knows where to write
        }
    },
}
resp = await client.post(OUTBOUND_URL, headers=headers, json=payload, timeout=30)
conversation_id = resp.json()["conversation_id"]
```

**Pass `session_id` and `listing_id` as dynamic variables.** They come back on the outcome webhook and are how you know which card to update. Getting this wrong means three calls all writing to the same card.

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

## Webhook tools

The agent's tools are HTTP webhooks declared in `agent/tools.json` and registered in the provider dashboard. The **description field is the prompt** — it's what the model reads to decide when to call the tool. Write it like you're briefing a person.

```json
{
  "type": "webhook",
  "name": "record_preferences",
  "description": "Call this as soon as the caller has described what they're looking for — bedrooms, neighbourhoods, budget, parking, pets. Call it again any time they change or reprioritize what matters. Do not wait until the end of the conversation.",
  "api_schema": {
    "url": "https://<ngrok>/agent/preferences",
    "method": "POST",
    "request_headers": { "Content-Type": "application/json" },
    "request_body_schema": {
      "type": "object",
      "properties": {
        "session_id": { "type": "string", "description": "The session id from dynamic variables." },
        "beds": { "type": "integer", "description": "Number of bedrooms wanted." },
        "max_rent": { "type": "integer", "description": "Maximum monthly rent in CAD." }
      },
      "required": ["session_id"]
    },
    "content_type": "application/json"
  }
}
```

Tools we need: `record_preferences` · `start_calls` · `book_viewing` · `record_outcome` (called on the realtor-facing agent).

**The webhook's return string is spoken aloud.** Keep responses under 25 words and write them as speech, not as JSON summaries.

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

1. Twilio number with **Voice and SMS** capability
2. Provider account, one agent per role, Twilio number imported → note the `phone_number_id`
3. ngrok running; put the URL into every tool in `agent/tools.json`
4. Register the tools in the dashboard
5. Test: place a call to your own phone, say something that should fire a tool, watch the server log

**Done when** you speak on a call and your FastAPI logs the tool call with its arguments. Until that works, nothing else in this lane matters.

## Gotchas

- Three simultaneous outbound calls may need more than one Twilio number. Test concurrency early, not at 14:00.
- ngrok URLs change on restart unless you reserve a subdomain. A restarted tunnel silently breaks every registered tool.
- Every `agent_phone` in `data/listings.json` is a teammate's number. We never cold-call real people with a bot.
- Provider dashboards cache tool definitions. After editing `tools.json`, re-sync and place a fresh test call.
