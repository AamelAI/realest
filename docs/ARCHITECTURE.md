# Architecture

One session store. Two channels. No audio code.

---

## The shape

```
                         ┌──────────────────────────┐
   caller's phone ──────▶│  Twilio Media Streams    │
        (inbound)        │    ⇅ OpenAI Realtime     │
                         └────────────┬─────────────┘
                                      │ function tools (in-process)
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

## Why OpenAI Realtime, and why the bridge is already written

Calls run on the **OpenAI Realtime API** with **Twilio Media Streams** proxying audio both ways. Marquee sponsor, event credits, no third-party voice vendor, nothing out of pocket.

The cost of that choice is audio plumbing — μ-law format, barge-in, `streamSid` — which is why `scripts/spike_bridge.py` was written and proven *before* the event. Build on it; don't rewrite it, and don't debug it during the build.

Tools are **in-process function calls**, not HTTP webhooks: the model emits `response.function_call_arguments.done`, the bridge calls the matching Python function directly and replies with a `function_call_output` that gets spoken aloud. No dashboard, no URLs to keep in sync.

**Consequence:** the state-mutating logic is still ordinary functions you can call from a test or a `curl` against `/agent/*`, with no phone involved. Use that — you can build and verify most of this project without dialling anything.

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

**Neighbourhoods are fuzzy on purpose.** Exact area match scores **30**, a walkable neighbour **14**, anywhere else **−30** (`NEARBY` in `server/listings.py`). A caller who says "King West" means "or near enough that I'd still go and see it" — strict matching returns an empty shortlist, which is worse than a Liberty Village unit one streetcar stop away. Exact hits always outrank neighbours, and the card shows the real neighbourhood, so nothing is hidden.

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
| Voice agents | `scripts/spike_bridge.py` | prompts in code, tools from `agent/tools.json`, sent in `session.update` |
| Listings | `data/listings.json` → SQLite | seeded before the event |
