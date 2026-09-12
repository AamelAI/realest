# Backlog

Three lanes, built to run in parallel. Put your names on the lanes at 11:00 and don't swap mid-build.

| Lane | Owns | Name |
|---|---|---|
| **D1** | The ear + the store — inbound voice, `SessionState`, preference extraction | |
| **D2** | The second line — outbound calls, `CallOutcome`, SMS, email fallback | |
| **D3** | The page — listings, ranking, the live surface | |

**One hard dependency:** `server/state.py`. Both other lanes import it. It gets agreed jointly in the first five minutes and frozen at 12:30.

Everything else is parallel by construction. If you find yourself waiting on someone, you're doing the wrong task — take the next one in your own lane.

---

## Before doors

| ID | Lane | Task | Done when |
|---|---|---|---|
| P1 | D1 | Twilio number (416/647, Voice **+** SMS). Verify all three teammate phones in the console | Number shows both capabilities; three phones verified |
| P2 | D1 | Voice provider account · create **renter agent** · import the Twilio number | Test call from the dashboard — your phone rings and the agent talks |
| P3 | D2 | ngrok **reserved static domain** | `curl https://<domain>/health` reaches your laptop from cellular |
| P4 | D2 | `.env` filled from `.env.example`; swap the ngrok URL into `agent/tools.json` | `make doctor` green |
| P5 | D3 | Create the **public submission repo**, push access for all three | All three can push. `base` stays private |
| P6 | D3 | `make install` · `make listings PHONE=… EMAIL=…` · `make seed` | `make doctor` green, 124 listings valid |
| P7 | D3 | Vercel project pointed at `web/` | Blank page deploys at a real URL |
| P8 | all | Pick the **four demo listings** from `make preview` and note the IDs | One dead, one with hidden add-ons, one cats-only, one filler |
| P9 | all | Read the demo script (`PLAYBOOK.md` §5) out loud once, together | You've found the two lines that don't work |

---

## 11:15 — joint, five minutes, everyone stops

| ID | Task | Done when |
|---|---|---|
| T0 | Agree the `SessionState` shape. Read `.claude/skills/session-state/` first | Committed and pushed. Nobody edits it again without saying so |

---

## Rung 1 — voice in, shortlist, voice out

*Target 12:15. The loop works with zero web. If nothing else lands, this is still a submission.*

| ID | Lane | Task | Done when |
|---|---|---|---|
| 1.1 | D1 | `state.py` — store, `mutate()` with the lock, `get()` | Two concurrent writes don't clobber |
| 1.2 | D1 | `POST /agent/preferences` → extract → re-rank → speak back | `curl` sets preferences, state reflects them |
| 1.3 | D1 | Renter agent prompt + `record_preferences` tool wired | You talk, server logs the tool call with arguments |
| 1.4 | D2 | `place_call()` — one POST, dynamic variables carry `session_id` + `listing_id` | `curl` your server, a teammate's phone rings |
| 1.5 | D2 | **Listing agent** created — opening line identifies it as an AI | It asks availability, real cost, pets |
| 1.6 | D3 | `listings.load()` + `rank()` | Three fixtures pass (see `.claude/skills/ranking/`) |
| 1.7 | D3 | `GET /api/state` returns serialized state | Enums come out as strings |

---

## Rung 2 — SMS link, static page

*Target 12:45.*

| ID | Lane | Task | Done when |
|---|---|---|---|
| 2.1 | D2 | SMS fires **5s into the call**, cancels if the call ended | Link arrives while you're still talking |
| 2.2 | D3 | `/s/<session_id>` — server-rendered card list with photos | Opens on a real phone over cellular |

---

## Rung 3 — one call result lands

*Target 13:15. This is the minimum version of the whole idea.*

| ID | Lane | Task | Done when |
|---|---|---|---|
| 3.1 | D2 | `extract_outcome()` — transcript → `CallOutcome` via structured outputs | Never invents a field. `source` always populated |
| 3.2 | D1 | `POST /agent/outcome` writes, then **re-ranks the whole list** | Card status changes, order changes |
| 3.3 | D3 | Card states: pending · calling · verified · dead · no-answer · booked | Readable at video scale from across a room |

---

## Rung 4 — live sync

*Target 13:30. **Gate 3** — one conversation ends in a booking with the page live.*

| ID | Lane | Task | Done when |
|---|---|---|---|
| 4.1 | D3 | `usePolling` at 1–1.5s, `no-store`, diff before `setState` | Reorder is visible while someone is still speaking |
| 4.2 | D3 | Reorder animation — Framer Motion `layout` | Positions interpolate, ~300ms, no snap |
| 4.3 | D1 | `POST /agent/book` — plain code does the write | Status → booked, SMS confirmation sent |

---

## Rung 5 — tap to confirm

| ID | Lane | Task | Done when |
|---|---|---|---|
| 5.1 | D3 | Checkboxes + one **Call these** button | Posts listing ids to `/agent/start-calls` |
| 5.2 | D2 | `fan_out()` — `asyncio.gather`, flip to `CALLING` **before** awaiting, 90s timeout each | Three cards go live simultaneously |

---

## Rung 6–7 — only if ahead at 13:30

| ID | Lane | Task |
|---|---|---|
| 6.1 | D2 | Hour-of-day check — agent **declines to dial** outside 9–19 and says why |
| 6.2 | D2 | `draft_email()` on no-answer; show on the card with a Send button |
| 7.1 | D2 | Three calls in parallel end to end |
| 7.2 | D1 | OpenRouter preset fallback on the reasoning path |
| 7.3 | D3 | Exa enrichment — transit, building reputation |

---

## 13:30 — harden and rehearse

| ID | Lane | Task |
|---|---|---|
| H1 | all | Run the full script end to end, three times. You're rehearsing a performance |
| H2 | D2 | Record a **clean backup take at 14:00** while the build still works |
| H3 | all | Put the no-answer → email beat on camera |

---

## 14:30 — feature freeze, whole team on artifacts

*Read `.claude/skills/submit/` first.*

| ID | Lane | Task |
|---|---|---|
| S1 | D1 | README — hook, GIF, **both call transcripts in full**, architecture diagram, prior art, ethics line, built-today-vs-scaffolded |
| S2 | D3 | The two-minute video. Three takes minimum, cut the best |
| S3 | D2 | Written description + **social post** tagging OpenAI, Georgian, CopilotKit, OpenRouter, AI Tinkerers, Human Feedback Foundation |
| S4 | D1 | Push to the **public** repo, verify it loads signed out |
| S5 | all | Submit by 15:10. Verify all five items present |

---

## If you fall behind

Cut in this order, and don't feel bad about any of it:

1. Rungs 6–7 entirely
2. Three parallel calls → **one** call, done perfectly
3. The reorder animation → cards just jump
4. Tap-to-confirm → voice confirmation only
5. Live polling → a page that updates on refresh

**Never cut:** the outbound call, the re-rank from a call outcome, or the artifacts hour. Those three are the submission.
