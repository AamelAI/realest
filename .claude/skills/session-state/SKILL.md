---
name: session-state
description: The shared SessionState contract that voice and page both depend on. Use when touching server/state.py, adding or changing a state field, writing anything that reads /api/state, or debugging why the page and the call disagree.
---

# Session state

`SessionState` is the only source of truth in this project. The voice agent writes it through webhook handlers; the page reads it by polling. Nothing else talks to anything.

**If you are about to wire the voice agent directly to the page, stop.** That is the thing that breaks at 14:00.

## The contract

Defined in `server/state.py`. Full field list in [docs/ARCHITECTURE.md](../../../docs/ARCHITECTURE.md#the-state-contract).

```
SessionState
  session_id   str
  preferences  Preferences
  listings     list[ListingState]   # ordered; index 0 is the top pick
  agent_says   str                  # last spoken line, for the page header
  updated_at   float
```

## Rules

**Keep it under ten top-level fields.** SITE COBRA's winning state object had three. Every field is one more thing the page must render and the agent must keep correct.

**Order carries meaning.** `listings` is the ranked shortlist. Never sort it in the page — the page renders what it's given, in the order it's given. Ranking happens server-side, once, in `listings.py`.

**Every mutation bumps `updated_at`.** The page diffs on the serialized payload; a stale timestamp means a missed render.

**Never mutate in place from two places at once.** Three calls land concurrently. Guard writes with a lock or funnel every mutation through one function in `state.py`. Two coroutines writing `listings` at the same time is a real bug here, not a theoretical one.

**`agent_says` is for humans, not for logic.** It's what the page header shows so the viewer can follow along without audio. Never branch on it.

## Reading it

```
GET /api/state?session=<session_id>  ->  SessionState as JSON
```

No auth. The session id is the secret, it expires with the session, and it's what makes the SMS link work. Don't build login.

## Writing it

Every write comes from a webhook handler in `server/main.py`:

| Endpoint | Writes |
|---|---|
| `POST /agent/preferences` | `preferences`, then re-ranks `listings` |
| `POST /agent/start-calls` | `listings[].status` → `CALLING` |
| `POST /agent/outcome` | `listings[].outcome`, `status`, then re-ranks |
| `POST /agent/book` | `listings[].status` → `BOOKED` |

Each handler returns a short string the voice agent reads aloud. Keep those under 25 words — the agent has to say them out loud and long returns sound robotic.

## Testing without a phone

You can build and verify almost all of this with `curl`. Do that instead of dialling.

```bash
curl -X POST localhost:8000/agent/preferences \
  -H 'content-type: application/json' \
  -d '{"session_id":"demo","beds":2,"areas":["King West"],"max_rent":3400,"parking":true}'

curl localhost:8000/api/state?session=demo | jq '.listings[] | {listing_id, rank, status}'
```

Keep a `scripts/seed_session.sh` that spins up a realistic session in one command. You'll run it fifty times today.

## Gotchas

- **Don't change the shape after 12:30.** Both other lanes import it. A rename at 13:00 costs the afternoon.
- **`outcome` is nullable and stays null until a human actually said something.** Never fabricate a `CallOutcome` to make the page look complete — the whole pitch is that these facts came from a person.
- **Serialize with `model_dump(mode="json")`.** Enums must come out as strings or the TypeScript side breaks silently.
