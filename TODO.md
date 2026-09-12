# TODO — build day

**Mark a task done by putting its id in your commit message:**

```bash
git commit -m "[1.4] tool dispatch wired"
```

`make todo` derives the board from `git log`. Nobody edits this file during the build.

---

## The seam

Everything routes through one function:

```python
dispatch(tool_name: str, args: dict, session_id: str) -> str   # spoken/shown reply
```

**Voice and text both call it.** D1/D2/D3 build the entire product against a **text chat** LLM. D4 builds the voice transport in parallel and swaps it in at Step 4. Nobody blocks on a phone.

Same for outbound calls — `CallTransport.place_call()` has a **stub** implementation returning canned transcripts. D2 builds the whole call→outcome→re-rank loop against the stub; D4 replaces it with the real thing.

| Lane | Owns |
|---|---|
| **D1** | The brain + the store — `SessionState`, `dispatch()`, the text chat loop |
| **D2** | Calls — `CallTransport`, `CallOutcome` extraction, re-rank trigger, email fallback |
| **D3** | Data + the page — listings, `rank()`, the live surface |
| **D4** | Voice, solely — Twilio, the bridge, TwiML, both call directions |

---

## Already done (last night)

`0.1` ngrok static domain · `0.35` key probe (`make keys`) · `0.6` deps + 124 listings · page template built (`web/`, ledger design) · public repo `AamelAI/realest` created

---

## Step 0 — unblock · now

- `0.2` **D4** — Twilio number (416/647, Voice + SMS) + all three phones in **Verified Caller IDs**
- `0.5` **D1** — push the `base` scaffold into `AamelAI/realest`, everyone works from there · *done when:* all four have pulled it
- `0.7` **D3** — Vercel project on `web/`, set `BACKEND_URL` · *done when:* page live at a real URL
- `0.8` **ALL** — pick the four demo listings from `make preview` · *done when:* one dead, one with add-ons, one cats-only, one filler

---

## Step 1 — the agent works over text · target 12:45

*No phone involved. If this lands, the product exists.*

- `1.0` **ALL** — agree `SessionState` + the `dispatch()` signature, five minutes, freeze it · *done when:* pushed
- `1.1` **D1** — `state.py`: store, `mutate()` with a lock, `get()` · *done when:* two concurrent writes don't clobber
- `1.2` **D1** — `dispatch()` — routes the four tools in `agent/tools.json` to real functions, returns a short spoken-style string · *done when:* `curl` fires each tool by name
- `1.3` **D1** — `POST /chat` — text in → LLM with tools → dispatch → text out, per session · *done when:* you can hold the whole demo conversation by typing
- `1.4` **D3** — `listings.load()` + `rank()` · *done when:* three fixtures pass (`.claude/skills/ranking/`)
- `1.5` **D3** — `GET /api/state` serialized · *done when:* enums come out as strings
- `1.6` **D2** — `CallTransport` interface + `StubTransport` returning canned transcripts after a delay · *done when:* the stub returns the Wellington add-ons transcript
- `1.7` **D4** — `make bridge` + `make tunnel` + `make spike TO=…` · *done when:* **your phone rings and the agent speaks**

---

## Step 2 — a call changes the ranking · target 13:15

*Still no phone. This is the minimum complete submission.*

- `2.1` **D2** — `start_calls` → transport → `extract_outcome()` via structured outputs · *done when:* never invents a field, `source` always set
- `2.2` **D1** — outcome lands in state → **re-rank the whole list** · *done when:* the top pick dies and the order visibly changes
- `2.3` **D2** — `book_viewing` → plain-code write → status booked
- `2.4` **D4** — outbound TwiML + `place_call()` against a real number · *done when:* a teammate's phone rings from code

---

## Step 3 — the page goes live · target 13:45

- `3.1` **D3** — point `BACKEND_URL` at the tunnel, `/s/[sid]` renders real state · *done when:* opens on a phone over cellular
- `3.2` **D3** — polling on, reorder animates · *done when:* the shortfall reorders while you type
- `3.3` **D1** — SMS the session link · *done when:* link arrives on a real phone
- `3.4` **D4** — listing-agent prompt, identifies as AI in sentence one

---

## Step 4 — swap voice in · target 14:00

*One line changes. Everything else is already proven.*

- `4.1` **D4** — `VoiceTransport` replaces `StubTransport` behind the same interface · *done when:* a real call produces a real `CallOutcome`
- `4.2` **D4** — inbound voice calls `dispatch()`, same as `/chat` · *done when:* speaking does what typing does
- `4.3` **ALL** — end-to-end on the phone once · *done when:* call → shortlist → call out → reshuffle → booking

> **If `4.1` isn't landing by 14:00, stop and demo the text path.** See "If voice doesn't land" below.

---

## Step 5 — only if ahead

- `5.1` **D2** — three calls in parallel (`asyncio.gather`, flip to CALLING before awaiting)
- `5.2` **D2** — email fallback on no-answer + hour-of-day check
- `5.3` **D3** — tap-to-confirm posts to `/agent/start-calls`
- `5.4` **D3** — Exa enrichment

---

## Step 6 — rehearse, freeze · 14:00–14:30

- `6.1` **ALL** — run the full script end to end, three times
- `6.2` **D4** — record a **clean backup take** while it works
- `6.3` **ALL** — put a failure on camera (no-answer, or a low-confidence outcome)

> **14:30 — feature freeze.**

---

## Step 7 — the submission · 14:30–15:10

- `7.1` **D1** — README: hook, GIF, **both transcripts in full**, architecture diagram, prior art, ethics line, built-today-vs-scaffolded
- `7.2` **D3** — the two-minute video, three takes minimum
- `7.3` **D2** — written description + **social post** tagging OpenAI, Georgian, CopilotKit, OpenRouter, AI Tinkerers, Human Feedback Foundation
- `7.4` **D4** — verify `AamelAI/realest` is public and loads signed out
- `7.5` **ALL** — submit by 15:10, all five items present

---

## If voice doesn't land

The text path is a complete product and it demos. But **the submission's central claim is that the agent phones a human and learns something no listing contains.** Without a real call that claim weakens badly.

Priority if you have to choose: **the outbound call to a listing agent matters more than inbound voice.** A demo where you *type* your preferences and the agent *phones a real person* keeps the whole pitch. The reverse does not.

So if D4 can only land one leg, land outbound.

## Cut order

Step 5 entirely → parallel calls become one call → reorder animation → live polling becomes refresh-to-update → inbound voice becomes text.

**Never cut:** the outbound call, the re-rank from a call outcome, or Step 7.
