# Architecture

One session store. Two channels. No audio code.

---

## The shape

```
                         ┌──────────────────────────┐
   caller's phone ──────▶│  managed voice agent     │
        (inbound)        │  (ElevenLabs ConvAI/Vapi)│
                         └────────────┬─────────────┘
                                      │ webhook tools
                                      ▼
  ┌───────────────────────────────────────────────────────────┐
  │                    FastAPI  (server/)                     │
  │                                                           │
  │   POST /agent/preferences   ← agent heard what they want  │
  │   POST /agent/start-calls   ← agent was told to go        │
  │   POST /agent/outcome       ← a call returned a result    │
  │   POST /agent/book          ← book it, plain code         │
  │   GET  /api/state           ← the page reads this         │
  │                                                           │
  │                  ┌─────────────────┐                      │
  │                  │  SessionStore   │  ◀── source of truth │
  │                  └─────────────────┘                      │
  └──────────┬────────────────────────────────────┬───────────┘
             │ outbound calls (fan-out)           │ poll 1–2s
             ▼                                    ▼
   3 × listing agents' phones            Next.js page (web/)
                                          on the caller's phone
```

Everything flows through `SessionStore`. The voice agent never talks to the page; the page never talks to the voice agent. If you find yourself wiring those together directly, stop — you're building the thing that will break at 14:00.

---

## The state contract

This is the most important object in the repo. Agree it in the first five minutes and do not change it after 12:30 — both other lanes import it.

```python
# server/state.py

class CallStatus(str, Enum):
    PENDING  = "pending"    # not called yet
    CALLING  = "calling"    # dialling / in progress
    VERIFIED = "verified"   # someone answered, we learned something
    DEAD     = "dead"       # unit is gone
    NO_ANSWER = "no_answer" # nobody picked up → email drafted
    BOOKED   = "booked"     # viewing confirmed

class Preferences(BaseModel):
    beds: int | None
    baths: int | None
    areas: list[str]
    max_rent: int | None
    parking: bool | None
    pets: str | None            # "dog" | "cat" | None
    extra_questions: list[str]  # what the caller asked us to ask

class CallOutcome(BaseModel):
    """What a human told us. This is the whole product."""
    available: bool | None
    real_rent: int | None        # rent + mandatory add-ons
    addons: list[str]            # "parking $180", "locker $40"
    pets_allowed: str | None     # "cats only"
    viewing_slot: str | None     # "Saturday 2:00pm"
    answers: dict[str, str]      # extra_questions → what they said
    source: str                  # "Mark, 1:42pm" — provenance for the card
    raw_transcript: str

class ListingState(BaseModel):
    listing_id: str
    status: CallStatus
    rank: int
    outcome: CallOutcome | None

class SessionState(BaseModel):
    session_id: str
    preferences: Preferences
    listings: list[ListingState]   # ordered — index 0 is the top pick
    agent_says: str                # last thing spoken, for the page header
    updated_at: float
```

**Keep it under ten top-level fields.** SITE COBRA's winning state object had three. Every field you add is a field the page has to render and the agent has to keep correct.

### Who writes what

| Field | Written by | Read by |
|---|---|---|
| `preferences` | voice agent via `/agent/preferences` | ranking, the page |
| `listings[].rank` | ranking, after every preference change and every outcome | the page |
| `listings[].status` | `calls.py` as each call progresses | the page |
| `listings[].outcome` | `calls.py` after `CallOutcome` extraction | ranking, the page |
| `agent_says` | every webhook | the page header |

---

## Request flow, end to end

1. **Caller dials.** Managed provider answers with our agent. No code of ours runs yet.
2. **Agent extracts preferences** → calls `POST /agent/preferences`. Server ranks listings, writes `SessionState`, returns a short confirmation string the agent reads aloud.
3. **Server texts the link.** Twilio SMS with `https://<vercel-app>/s/<session_id>`. Fire this ~5s into the call, like SITE COBRA did — it lands while the caller is still talking.
4. **Page opens and polls** `/api/state?session=<id>` every 1–2s. Renders cards from `listings`.
5. **Caller changes priorities** → agent calls `/agent/preferences` again → re-rank → the page reorders mid-sentence. **This is the money shot.**
6. **Caller taps three cards**, or tells the agent → `POST /agent/start-calls` with listing ids.
7. **Fan-out.** `asyncio.gather` over three outbound calls. Each flips its card to `CALLING` immediately.
8. **Each call returns** → extract `CallOutcome` from the transcript with structured outputs → write to state → **re-rank** → the page reshuffles.
9. **No answer / wrong hour** → status `NO_ANSWER`, draft an email, surface it on the card with a send button.
10. **Caller picks a slot** → `POST /agent/book` → plain-code write → status `BOOKED` → Twilio SMS confirmation.

---

## Why webhook tools, not a custom audio pipeline

The voice agent's tools are declared as HTTP webhooks pointing at our FastAPI. The provider handles every hard part of telephony — audio format, barge-in, interruption, turn-taking — and calls us with structured arguments when the conversation needs something.

SITE COBRA's entire telephony layer was 182 lines and one POST. Ours should be similar. See `.claude/skills/voice-calls/` for the exact patterns and `agent/tools.json` for the tool definitions.

**Consequence:** all our logic is ordinary HTTP handlers we can test with `curl`, with no phone involved. Use that — you can build and test 90% of this project without dialling anything.

---

## Ranking

Ranking runs on two triggers: a preference change, and a call outcome landing. It is a pure function.

```
rank(listings, preferences, outcomes) -> ordered list
```

Rules, in order of force:

1. `DEAD` sinks to the bottom, always.
2. `real_rent` (rent + mandatory add-ons) beats listed rent when we have it. If `real_rent > max_rent`, it's over budget — demote hard.
3. `VERIFIED` outranks `PENDING` at equal fit. Confirmed beats hypothetical.
4. Then weighted preference fit, with the weights the caller stated most recently.
5. Hard conflicts (dog vs cats-only) don't remove a listing — they annotate it. The caller decides.

Rule 5 matters: the agent surfaces the conflict and lets the human choose. That's the controllability story.

---

## Failure handling

Named explicitly in the rubric's top band, and cheap.

| Failure | Behaviour |
|---|---|
| Listing agent doesn't answer | Status `NO_ANSWER`, draft an email, tell the caller, offer to retry |
| Outside business hours | Agent **declines to dial** and offers email or Monday. Say it out loud — it's judgment, not a retry |
| Model call fails | OpenRouter preset falls through to the next model |
| `CallOutcome` extraction is low confidence | Keep the raw transcript on the card. Never invent a fact a human didn't say |
| Polling dies | Voice loop completes regardless. The page is an enhancement |

---

## What runs where

| Piece | Where | Note |
|---|---|---|
| FastAPI | laptop behind ngrok | needs a long-running process; don't deploy to anything that scales to zero |
| Next.js page | Vercel | the SMS link must be a real public URL |
| Voice agent config | provider dashboard | prompt + tools, changeable without redeploy |
| Listings | `data/listings.json` → SQLite | seeded before the event |
