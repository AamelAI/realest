# Preflight — everything to do before doors

**Realest** · by AAMEL · Agents, Everywhere · Toronto · Sep 12

Companion to [PLAYBOOK.md](PLAYBOOK.md), which covers strategy, the demo script and the scorecard. This file is the stack decision and the setup checklist.

---

## 0. Two findings first

**`AamelAI/base` is empty.** Cloned and verified — zero commits, zero refs, 0 KB, created 06:23 UTC today. There is no architecture doc, no sponsor notes and no skeleton in it. Whatever you thought you pushed didn't land. Everything below assumes we're scaffolding from nothing, which is fine — the repo being brand-new and empty also makes eligibility airtight.

**It's private.** A **public** GitHub repo is one of the five required submission items. Flip it before 15:30 or the submission is incomplete.

---

## 1. The decision that saves your day

I read SITE COBRA's source (3rd place, Poland — the closest analogue to what we're building). The most important thing in that repo is what they *didn't* build.

**Their entire telephony layer is 182 lines of Python and one HTTP POST.**

```python
POST https://api.elevenlabs.io/v1/convai/twilio/outbound-call
{
  "agent_id": ELEVENLABS_AGENT_ID,
  "agent_phone_number_id": ELEVENLABS_PHONE_NUMBER_ID,
  "to_number": "+1416...",
  "conversation_initiation_client_data": {
    "dynamic_variables": { "business_name": ..., "business_type": ... }
  }
}
```

That's it. They never touched audio. No μ-law encoding, no media-stream websocket, no barge-in handling, no interruption logic — the managed conversational-telephony provider owns all of it. The agent's behaviour lives in a dashboard, its tools are declared as **webhooks** in a JSON file, and their own server just exposes small endpoints for the agent to call.

**This removes the single biggest risk in our plan.** My earlier Gate 2 ("by 12:30 you must hear the agent and dial out") assumed 90 minutes of audio plumbing. On a managed platform it's a 20-minute task you can finish before doors.

### Their architecture, which we should copy almost exactly

| SITE COBRA | Ours |
|---|---|
| Managed voice agent places the call | Same |
| Agent tools = webhooks → their FastAPI | Agent tools = webhooks → our FastAPI |
| `LiveDemoState` — **three fields** | `SessionState` — keep it under ten |
| Next.js page polls `/api/state` every **2000ms** | Poll every 1000–2000ms. Not websockets |
| Twilio SMS with the live link sent **5s into the call** | Same trick — link arrives while you're still talking |
| Poll `/v1/convai/conversations/{id}` for status + transcript | Same, for call outcomes |
| Page on Vercel, backend on a laptop behind ngrok | Same |

Two details worth stealing outright: they sent the SMS **during** the call, not after, and they cancelled it if the call ended early. And their state object was three booleans-and-a-string — the discipline is the point.

---

## 2. Stack, section by section

| Layer | Use | Why | Fallback |
|---|---|---|---|
| **Voice transport** | ElevenLabs Conversational AI + a Twilio number (or Vapi / Retell) | One POST places a call. Provider owns audio format, barge-in, interruption. Proven at 3rd place | OpenAI Realtime + Twilio Elastic SIP trunk — sponsor-aligned, more setup today |
| **Agent behaviour** | Dashboard prompt + `agent/tools.json` webhook definitions | No redeploy to change what the agent says. Tools point at our server | — |
| **Backend** | Python 3.12 · FastAPI · uvicorn | Team strength, async-native for three concurrent calls, matches COBRA | — |
| **Reasoning + extraction** | OpenAI Agents SDK + **structured outputs** for `Preferences` and `CallOutcome` | Marquee sponsor stays genuinely central even though transport is managed. `CallOutcome` is what makes call results *rankable* instead of just transcribed | — |
| **Model gateway** | OpenRouter preset with a fallback chain | Criterion-3 "thoughtful failure handling" for ~15 minutes of work | — |
| **State** | One in-memory dict keyed by session id + SQLite for listings | Voice writes it, page reads it. Everything hangs off this — build it first | — |
| **Live page** | Next.js 15 App Router · Tailwind · shadcn/ui · `usePolling` | Exactly COBRA's shape. Deploy to Vercel so the SMS link is a real URL | — |
| **Generative UI** | CopilotKit AG-UI **only if someone is already fluent** | It's the named award, but don't let award-chasing sink the build | Plain React + poll |
| **Parallel calls** | `asyncio.gather` over three call tasks | COBRA used raw `asyncio.create_task`. Simple is fine | Trigger.dev for durable timeouts if you want the sponsor story |
| **Listings** | 50 seeded Toronto rentals in SQLite/JSON, collected before the build | Live scraping fails on camera. COBRA used Apify for Google Maps if you want live data | Apify |
| **Enrichment** | Exa `/search` with highlights — transit, building reputation | Sponsor; Exa credits ride on all three podium places | skip |
| **SMS** | Twilio, same account as the number | — | — |
| **Email fallback** | Resend (one API call, no SMTP) — or draft-and-display only | Don't build mail plumbing under time pressure | draft-only |
| **Tunnel** | ngrok (reserve a static subdomain if you can) | Twilio and the voice provider must reach your laptop | cloudflared |
| **Hosting** | Page on Vercel · backend local behind ngrok | Cloud Run scale-to-zero kills live sessions. COBRA did exactly this | — |

**On sponsor alignment:** the calls are the product — whatever gets calls working fastest wins. Managed transport plus OpenAI for every reasoning step is honest and defensible: *"OpenAI Agents SDK and structured outputs drive ranking, call-outcome extraction and email drafting; telephony transport is managed."* Say it that way in the README.

---

## 3. Repo skeleton to scaffold

```
base/
├── README.md            ← becomes the submission README
├── PLAYBOOK.md          ← strategy, demo script, scorecard
├── PREFLIGHT.md         ← this file
├── .env.example
├── .gitignore
├── agent/
│   └── tools.json       ← webhook tool definitions for the voice agent
├── server/
│   ├── main.py          ← /call · /api/state · webhook endpoints
│   ├── state.py         ← THE session store — build this first
│   ├── listings.py      ← load + rank
│   ├── calls.py         ← outbound fan-out, CallOutcome extraction
│   └── requirements.txt
├── web/
│   ├── app/page.tsx     ← the card list
│   ├── lib/usePolling.ts
│   └── package.json
└── data/
    └── listings.json    ← 50 seeded Toronto rentals
```

---

## 4. The checklist

Ordered by risk, not by sequence. **It's ~2:40am and doors are at 10:00 — if you have to choose, sleep beats P2.** A tired team at 11:15 is worse than a team missing a checkbox.

### P0 — must be done before doors (~90 min)

| | Task | Done when |
|---|---|---|
| 1 | **Twilio account + a Canadian number** with Voice **and** SMS capability | The number shows both capabilities in console |
| 2 | **Voice provider account**, create one agent, import the Twilio number | You trigger a test call from the dashboard and **your own phone rings and the agent talks** |
| 3 | **ngrok running**, URL noted | `curl https://<sub>.ngrok-free.app/health` from your phone's data connection returns 200 |
| 4 | **Repo public + skeleton pushed** | `gh repo view AamelAI/base --web` loads while signed out |
| 5 | **All keys in `.env`**, `.env.example` committed, `.env` gitignored | `git status` shows no `.env` |

### P1 — do if you have another hour (~60 min)

| | Task | Done when |
|---|---|---|
| 6 | **`POST /call`** endpoint — copy COBRA's shape | `curl` your local server, your phone rings |
| 7 | **One webhook tool** on the agent (`record_outcome`) pointing at ngrok | You say something on the call and your server logs the tool call with its arguments |
| 8 | **50 seeded listings** in `data/listings.json` — address, rent, beds, baths, parking, pets, amenities, transit, **photo URL**, `agent_phone` | Every `agent_phone` is a teammate's real number. Photos are stock interiors, noted as such in the README |

### P2 — can happen during the build (~60 min)

| | Task | Done when |
|---|---|---|
| 9 | **Next.js page on Vercel** polling `/api/state` | Change state via `curl`, deployed page updates within 2s |
| 10 | OpenRouter preset + fallback chain | — |
| 11 | Exa key, one test query | — |

### Free, and worth more than item 11

**Read the demo script in PLAYBOOK.md §5 out loud once, together.** Fifteen minutes. You are rehearsing a performance, and the first time you hear it out loud you will find two lines that don't work.

---

## 5. Do NOT do tonight

Eligibility says **core functionality must be built during the event**. Accounts, keys, SDK installs, an empty skeleton, a `/health` route, seed data and a deployed blank page are all explicitly allowed — templates and starter code are fine.

What you must **not** pre-build: the ranking logic, the call orchestration, `CallOutcome` extraction, the reshuffle, the email decision. That's the project. Write it between 11:15 and 14:30, and keep the commit history clean enough to prove it.

A one-line note in the README — *"scaffolding and credentials prepared the night before; all agent logic, ranking, call orchestration and the live surface built during the event"* — answers the question before a judge asks it.

---

## 6. First thirty minutes of the build

1. **`server/state.py` before anything else.** Agree the shape of `SessionState` in five minutes flat. Both other lanes import it, and if it changes at 13:00 you lose the afternoon.
2. Dev 1 wires inbound. Dev 2 wires the fan-out on top of the working `/call`. Dev 3 loads listings and renders the card list against a hardcoded state object.
3. Integrate at 12:30 with stubs, ugly. Then climb the ladder in PLAYBOOK.md §6 in order.

---

*Reference: [SITE COBRA source](https://github.com/PiotrTyrakowski/DeepMindHackaton) — 3rd place, AI Tinkerers Poland, March 2026. Read `voicebotcall/main.py`, `elevenlabs-tools.json` and `client-website/lib/usePolling.ts` before you write any telephony code.*
