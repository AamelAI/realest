# Realest

**Which listings are actually real.**

Built by **AAMEL** for *Agents, Everywhere: Bots, Channels, & More* — Toronto, September 12 2026.

> Every AI voice agent in real estate works for the brokerage. Realest works for the renter — you talk, a page in your hand reorders as you talk, and it phones three listing agents at once to find out which listings are actually real.

---

## What it does

You phone it and say what you're after. It texts you a link, and a page in your hand fills with listings — photos, rent, beds, transit. Keep talking and the page reorders itself as your priorities change.

Then it asks the question that makes it more than a search tool: *"Listings go stale fast. Want me to call and check they're real? Anything else you want me to ask?"*

You tap three. It calls all three **at once**. One is already leased. One is $180/month more than listed once parking is in. One is available Saturday at two — cats only, and you mentioned a dog. Your shortlist inverts, and every reason came from a human who answered a phone thirty seconds ago.

If nobody picks up, or it's the wrong hour to be calling, it drafts an email instead and tells you.

---

## Why it can't be a chatbox

1. **It phones third parties.** A chat window cannot.
2. **The deciding information exists nowhere online.** *Is it still available, what does parking really cost, will you take a dog* lives in a leasing agent's head until someone asks. No model, index or scrape retrieves it. The agent **creates** the data by talking to a human.
3. **Voice and screen are one live session.** Not a transcript, not a web app — one conversation rendered twice, each channel doing what it's good at.

---

## Start here

| File | What's in it |
|---|---|
| **[CLAUDE.md](CLAUDE.md)** | The brief. Read before writing any code — scope, hard rules, conventions |
| **[PLAYBOOK.md](PLAYBOOK.md)** | Strategy: rubric decode, winner analysis, demo script, build ladder, scorecard |
| **[PREFLIGHT.md](PREFLIGHT.md)** | Setup checklist and the stack decision, with rationale |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | System design, the state contract, request flow, failure handling |
| **[docs/SPONSORS.md](docs/SPONSORS.md)** | Every sponsor tool, what it's for, and which we're using |

### Skills

Task-specific guides in `.claude/skills/`. Load the matching one before starting that piece — they carry the contracts and the gotchas.

| Skill | Load when |
|---|---|
| `session-state` | Touching `SessionState` or anything reading `/api/state` |
| `voice-calls` | Wiring the voice agent, outbound calls, webhook tools |
| `ranking` | Ranking listings or merging call outcomes |
| `live-surface` | Building or changing the page |
| `submit` | Packaging the submission at 14:30 |

---

## Layout

```
server/    FastAPI — the whole backend
  schemas.py   pydantic models that cross a boundary
  state.py     THE session store — single source of truth
  listings.py  load + rank
  calls.py     outbound fan-out, CallOutcome extraction
  main.py      /call · /api/state · webhook endpoints
web/       Next.js live page (polls /api/state)
agent/     tools.json — webhook tool definitions for the voice agent
data/      seeded Toronto listings
docs/      architecture, sponsors
```

---

## Setup

```bash
cp .env.example .env    # fill in keys
make install            # uv sync + npm install
make seed               # validate data/listings.json
make dev                # FastAPI on :8000
make tunnel             # ngrok — put the URL into agent/tools.json
make web                # Next.js on :3000
```

Then `make doctor` — it tells each machine exactly what's still missing.

Requires [`uv`](https://docs.astral.sh/uv/), `node` and `ngrok`. Python is pinned to 3.12 in `.python-version`.

**Intel Mac note:** `cryptography` is pinned `<47` in `pyproject.toml` — newer releases ship no macOS x86_64 wheel and fall back to a Rust source build that fails. Don't relax that pin today.

Copy `data/listings.sample.json` to `data/listings.json` and expand to ~50 rows. **Every `agent_phone` must be a teammate's real number** — we never cold-call strangers with a bot.

---

## Stack

Managed conversational telephony + Twilio · Python 3.12 / FastAPI · OpenAI Agents SDK with structured outputs for `Preferences` and `CallOutcome` · OpenRouter preset for fallback · Next.js on Vercel polling a FastAPI backend behind ngrok · Exa for card enrichment.

We do not write audio code. A managed provider owns audio format, barge-in and interruption entirely — see `.claude/skills/voice-calls/`.

---

## How it behaves around real people

- Identifies itself as an AI in the first sentence of every outbound call
- Calls only listings you explicitly selected. It never cold-dials
- Won't place calls outside business hours — it says so and offers email instead
- Every call-derived fact carries its provenance on the card: *"parking $180 — Mark, 1:42pm"*
- Never records a fact a human didn't say

---

## Prior art

The category exists, but entirely on the other side of the table. EliseAI, Funnel, Yardi Chat IQ, CloudTalk and Bland all sell **inbound** lead capture to property managers — they answer the phone, qualify you, and book you into the brokerage's calendar.

Realest is the inverse: it represents the renter and dials outward. That side isn't a shipped product anywhere we could find.

---

## Status

This repo (`AamelAI/base`) is the **private team template**. Clone it, build on it, and push the finished project to the **public submission repo** — that public URL is what goes in the submission form.

Pre-event scaffold only: credentials, dependencies, seed data and empty module stubs, all explicitly permitted. Every stub carries a `TODO(hackathon)` marker; all agent logic, ranking, call orchestration and the live surface are built during the event (11:15–15:30).
