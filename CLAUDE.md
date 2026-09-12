# Realest — agent context

Read this before writing any code in this repo. It is the shared brief for every teammate and every coding agent working on this project.

## What we are building

**Realest** — a voice agent that represents the *renter*, not the brokerage.

You phone it. You describe what you want. It texts you a link, and a page in your hand reorders itself as you keep talking. When you ask it to, it calls three listing agents **at once**, asks them the things listings never say — is it still available, what does parking actually cost, will you take a dog — and re-ranks your shortlist from what those humans said. Then it books the viewing and texts you the confirmation. If nobody picks up, or it's the wrong hour to be calling, it drafts an email instead and says so.

Built by **AAMEL** for *Agents, Everywhere* (Toronto, Sep 12 2026). Strategy, demo script and scoring live in [PLAYBOOK.md](PLAYBOOK.md). Setup and stack rationale live in [PREFLIGHT.md](PREFLIGHT.md). **Your tasks are in [BACKLOG.md](BACKLOG.md)** — find your lane, take the next item.

## The one thing that matters

The judging rubric's top band for innovation reads: *"reveals a surprising new agent pattern whose central value could not be reproduced in a standalone chatbox."*

Everything we build serves three claims:

1. **It phones third parties.** A chat window cannot.
2. **The deciding information exists nowhere online.** It lived in a leasing agent's head until our agent asked. We don't retrieve that data — we create it.
3. **Voice and screen are one live session.** Not a transcript, not a web app. One conversation rendered twice.

If a change doesn't serve one of those, it's out of scope today.

## Non-negotiables

- **One loop.** Talk → shortlist on your phone → brief the agent → tap which to call → parallel calls → the page reshuffles → book → SMS. Nothing else.
- **Build in ladder order.** See PLAYBOOK.md §6. Do not start a rung until the one below it works. Every rung is independently shippable.
- **Feature freeze 14:30.** Nothing written after that reaches a judge.
- **The page is never load-bearing.** If polling dies or the phone locks, the voice loop still completes, still books, still texts.

## Hard rules

| Rule | Why |
|---|---|
| **Poll, don't socket.** 1–2s poll against `/api/state` | A 3rd-place winner shipped exactly this. Websockets can drop mid-take; polling can't |
| **Never block speech on a network call** | Rank in memory, pre-fetch enrichment. Dead air reads as broken |
| **Booking is plain code** | The model calls `book_viewing(listing_id, slot)`; the function does the write. Models improvising state changes is how live demos fail |
| **Seeded listings only** | No live scraping. A scrape that fails on camera has no recovery |
| **Don't touch the audio bridge** | `scripts/spike_bridge.py` already handles μ-law, barge-in and streamSid. Build on it, don't rewrite it |
| **Every listing's `agent_phone` is a teammate's number** | We never cold-call real people with a bot |
| **UI must not look vibe-coded** | No cards-with-rings, pill badges, all-caps labels, coloured left stripes, backdrop-blur, gradients or Inter. Read `.claude/skills/live-surface/design-rules.md` **before** touching `web/` |

## Architecture in one paragraph

A single **session store** is the source of truth. The voice agent writes to it through webhook tools; the web page reads it by polling. Nothing else talks to anything. Audio rides OpenAI Realtime through a Twilio Media Streams bridge that was written and proven before the event. Reasoning (preference extraction, call-outcome extraction, ranking, email drafting) is OpenAI structured outputs behind an OpenRouter fallback. Full detail and the exact state contract: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
phone ──▶ managed voice agent ──webhooks──▶ FastAPI ──▶ SessionStore
                   ▲                            │            │
                   └──── outbound calls ────────┘            ▼
                                              Next.js page ──┘ (polls /api/state)
```

## Stack — already decided, don't re-litigate

| Layer | Choice |
|---|---|
| Voice | **OpenAI Realtime** over Twilio Media Streams. Marquee sponsor, event credits, nothing out of pocket |
| Backend | Python 3.12 · FastAPI · uvicorn |
| Reasoning | OpenAI Agents SDK + structured outputs |
| Model fallback | OpenRouter preset |
| Live page | Next.js 15 App Router · Tailwind · polling |
| Data | SQLite / JSON, 50 seeded Toronto rentals |
| Enrichment | Exa |
| SMS + number | Twilio |
| Tunnel | ngrok |

Every sponsor tool, what it's good for and which to reach for: [docs/SPONSORS.md](docs/SPONSORS.md).

## Layout

```
server/    FastAPI — the whole backend
  state.py     THE session store. Read the skill before touching it
  listings.py  load + rank
  calls.py     outbound fan-out, CallOutcome extraction
  main.py      /call · /api/state · webhook endpoints
web/       Next.js live page
agent/     tools.json — webhook tool definitions for the voice agent
data/      seeded listings
docs/      architecture, sponsors
.claude/skills/   task-specific guides — load the relevant one before starting
```

## Skills

Load the matching skill before you start that piece of work. They carry the contracts and the gotchas.

| Skill | Use when |
|---|---|
| `session-state` | Touching `SessionState` or anything that reads/writes it |
| `voice-calls` | Wiring the voice agent, placing calls, adding webhook tools |
| `ranking` | Ranking listings or merging call outcomes back into the shortlist |
| `live-surface` | Building or changing the page |
| `submit` | Packaging the submission at 14:30 |

## Conventions

- Python: type hints everywhere, `pydantic` models for anything crossing a boundary, `async def` for I/O.
- Every model-facing schema is a pydantic model in `server/schemas.py`. Never hand-parse JSON out of a model response.
- TypeScript strict. No `any` on anything that comes from `/api/state`.
- Keep functions short enough to read at 14:00 on four hours of sleep.
- Commit often with real messages — the commit history is how we prove what was built during the event.

## Closing tasks — do this on every commit

Work is tracked in [TODO.md](TODO.md). **Put the task id in square brackets in the commit message** and it closes automatically:

```bash
git commit -m "[1.4] outbound call places and rings"
git commit -m "[1.6] [1.7] ranking + state endpoint"   # several at once
```

`make todo` derives the board from `git log` — nobody edits TODO.md during the build, so there is nothing to merge-conflict on. If you finish a task and don't tag the commit, **your teammates cannot see it is done.**

Before you start a piece of work, run `make todo MINE=D1` (or D2/D3) to find the next task in your lane.

## Repos

`AamelAI/base` (this one) is the **private team template**. Work happens in clones of it. The finished project is pushed to a **separate public repo**, and that public URL is the submission. Don't paste a `base` link into the submission form.

## Eligibility

Core functionality must be built **during** the event (11:15–15:30). Scaffolding, credentials, dependencies, seed data and empty module stubs were prepared beforehand and are explicitly allowed; so are templates, libraries and prompts.

**Anything in this repo with a `TODO(hackathon)` marker must be written during the event.** Don't remove those markers before 11:15.
