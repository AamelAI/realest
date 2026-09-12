# TODO — build day

Steps run in order. Within a step, the three lanes run in parallel.

**Mark a task done by putting its id in your commit message:**

```bash
git commit -m "[1.4] outbound call places and rings"
```

Then `make todo` shows the board. Nobody edits this file during the build — progress is derived from git log, so there's nothing to merge-conflict on.

| Lane | Owns | Name |
|---|---|---|
| **D1** | The ear + the store — inbound voice, `SessionState`, preference extraction | |
| **D2** | The second line — outbound calls, `CallOutcome`, SMS, email | |
| **D3** | The page — listings, ranking, the live surface | |

---

## Step 0 — keys and first ring · before 11:15

Nothing else can start until `0.4` rings. If it doesn't by 11:45, take the fallback in `0.9`.

- `0.1` **D1** — ngrok authtoken for the account holding `zipping-scarf-actress.ngrok-free.dev`; `ngrok config add-authtoken <token>` · *done when:* `make tunnel-test` prints OK
- `0.2` **D1** — Twilio account, buy a 416/647 number with **Voice + SMS** · *done when:* number shows both capabilities
- `0.3` **D1** — add all three teammate phones to **Verified Caller IDs** · *done when:* all three listed
- `0.35` **D1** — `make keys` — confirm the OpenAI key reaches the **API**, not just Codex · *done when:* it prints a realtime model, or you've picked a fallback in `docs/VOICE_FALLBACK.md`
- `0.4` **D1** — `OPENAI_API_KEY` + `TWILIO_*` into `.env`; `make bridge` · `make tunnel` · `make spike TO=…` · *done when:* **your phone rings, the agent speaks, and it stops when you interrupt**
- `0.5` **D2** — create the **public submission repo**, push access for all three · *done when:* everyone can push
- `0.6` **D2** — `make install`; `make listings PHONE=… EMAIL=…`; `make seed` · *done when:* `make doctor` green
- `0.7` **D3** — Vercel project on `web/`, set `BACKEND_URL` env var · *done when:* blank page live at a real URL
- `0.8` **ALL** — pick the four demo listings from `make preview`, note the ids · *done when:* one dead, one with add-ons, one cats-only, one filler
- `0.9` **ALL** — if `0.4` fails by 11:45: switch inbound to browser-mic WebRTC, keep outbound calls · *done when:* decision made out loud

---

## Step 1 — the loop works with zero web · target 12:15

- `1.0` **ALL** — agree the `SessionState` shape, five minutes, then freeze it · *done when:* committed and pushed
- `1.1` **D1** — `state.py`: store, `mutate()` with the lock, `get()` · *done when:* two concurrent writes don't clobber
- `1.2` **D1** — `POST /agent/preferences` → extract → re-rank → speak back · *done when:* `curl` sets preferences, state reflects them
- `1.3` **D1** — renter prompt + `record_preferences` tool dispatching in-process · *done when:* you talk, the bridge logs the call with arguments
- `1.4` **D2** — `place_call()`, session/listing carried in the TwiML query string · *done when:* `curl` your server, a teammate's phone rings
- `1.5` **D2** — listing-agent prompt, identifies as AI in sentence one · *done when:* it asks availability, real cost, pets
- `1.6` **D3** — `listings.load()` + `rank()` · *done when:* the three fixtures pass
- `1.7` **D3** — `GET /api/state` serialized · *done when:* enums come out as strings

---

## Step 2 — SMS and the page · target 12:45

- `2.1` **D2** — SMS fires **5s into the call**, cancels if it already ended · *done when:* link arrives while you're still talking
- `2.2` **D3** — `/s/[sid]` server-rendered card list with photos · *done when:* opens on a real phone over cellular
- `2.3` **D3** — `/api/state` proxy route on Vercel · *done when:* the phone never resolves ngrok

---

## Step 3 — a call result lands · target 13:15

*The minimum version of the whole idea. If you stop here you still have a submission.*

- `3.1` **D2** — `extract_outcome()` via structured outputs · *done when:* never invents a field; `source` always set
- `3.2` **D1** — `POST /agent/outcome` writes, then re-ranks **the whole list** · *done when:* status changes and order changes
- `3.3` **D3** — six card states, readable at video scale · *done when:* dead sinks and reads as dead from across a room

---

## Step 4 — live sync · **Gate: 13:30**

- `4.1` **D3** — `usePolling` at 1–1.5s, `no-store`, diff before `setState` · *done when:* reorder visible while someone is still speaking
- `4.2` **D3** — reorder animation, Framer Motion `layout`, ~300ms · *done when:* positions interpolate, no snap
- `4.3` **D1** — `POST /agent/book`, plain code does the write · *done when:* status booked, SMS confirmation sent

> **13:30 gate:** one conversation ends in a booking with the page live. If not, freeze here and go to Step 7.

---

## Step 5 — tap to confirm

- `5.1` **D3** — checkboxes + one **Call these** button · *done when:* posts ids to `/agent/start-calls`
- `5.2` **D2** — `fan_out()`: flip to `CALLING` before awaiting, 90s timeout each, `return_exceptions=True` · *done when:* three cards go live simultaneously

---

## Step 6 — only if ahead at 13:30

- `6.1` **D2** — hour-of-day check: agent **declines to dial** outside 9–19 and says why
- `6.2` **D2** — `draft_email()` on no-answer, shown on the card with a Send button
- `6.3` **D1** — OpenRouter preset fallback on the reasoning path
- `6.4` **D3** — Exa enrichment: transit, building reputation

---

## Step 7 — rehearse, then freeze · 13:30–14:30

- `7.1` **ALL** — run the full script end to end, three times · *done when:* no stumbles
- `7.2` **D2** — record a **clean backup take at 14:00** while the build still works
- `7.3` **ALL** — no-answer → email beat on camera

> **14:30 — feature freeze.** Nothing built after this reaches a judge.

---

## Step 8 — the submission · 14:30–15:10

*Read `.claude/skills/submit/` first.*

- `8.1` **D1** — README: hook, GIF, **both call transcripts in full**, architecture diagram, prior art, ethics line, built-today-vs-scaffolded
- `8.2` **D3** — the two-minute video, three takes minimum
- `8.3` **D2** — written description + **social post** tagging OpenAI, Georgian, CopilotKit, OpenRouter, AI Tinkerers, Human Feedback Foundation
- `8.4` **D1** — push to the **public** repo, verify it loads signed out
- `8.5` **ALL** — submit by 15:10, verify all five items present

---

## If you fall behind

Cut in this order: Step 6 entirely → three calls become one perfect call → the animation → tap-to-confirm → live polling becomes refresh-to-update.

**Never cut:** the outbound call, the re-rank from a call outcome, or Step 8.
