# Stack — what we use, and what we deliberately don't

Decisions are made. If you're about to add something that isn't here, it's out of scope for today.

## Use

| Layer | Pick | Why |
|---|---|---|
| Python env | **`uv`** — `uv sync`, `uv run` | Seconds not minutes, lockfile, pins the Python version. SITE COBRA shipped with `uv.lock` |
| Backend | FastAPI + uvicorn | Async-native (needed for three concurrent calls), pydantic built in, free `/docs` page that screenshots well |
| Data | **No database.** JSON → dict at startup | 50 read-only listings, ephemeral sessions. If the process dies mid-demo you're re-running the demo anyway |
| Tunnel | ngrok with a **reserved static domain** | Tool webhook URLs are registered provider-side. A changed URL on restart silently breaks every tool |
| Voice | Managed conversational telephony | See `.claude/skills/voice-calls/`. We never touch audio |
| Frontend | Next.js 15 · Tailwind · **shadcn/ui** | Copy-paste cards, no theming setup, looks finished immediately |
| Reorder animation | **Framer Motion `<motion.div layout>`** | Highest value-per-minute in the build. One prop gives the FLIP transition, and that reorder *is* the money shot |
| Models | `openai` structured outputs · OpenRouter for fallback | `CallOutcome` extraction is where this matters |
| Email | **Resend** | One POST, no SMTP, no domain verification |
| Logging | `logging` with `session_id` on every line | `logfire.instrument_fastapi(app)` is one line if you want a trace screenshot for the README |
| Tests | Three pytest fixtures for `rank()`, nothing else | If "top pick unavailable" and "add-ons push #2 over budget" both produce the demo reshuffle, the demo works |

## Don't use

**Docker.** You're solving "one command to run it" — the Makefile does that in six lines. The real cost is that the voice provider must reach ngrok and ngrok must reach FastAPI; a container network between them is the thing that eats an hour at 13:00. Plus flaky file-watching on macOS. An untested Dockerfile in the repo is worse than none: a judge who tries it and fails scores you down.

**A database.** Postgres, Redis, an ORM, migrations — nothing here needs persistence.

**pgvector / RAG / embeddings.** We have 50 rows of structured fields and a structured query (`beds`, `max_rent`, `areas`, `parking`). That's a filter and a weighted sort. Cosine distance over listing prose will hand you a 1-bedroom at $4,000 because it "sounds similar"; `WHERE beds = 2 AND rent <= 3400` cannot make that mistake. And an embedding call is a network round trip **in the middle of a live phone call** — that's dead air, and dead air reads as broken. SITE COBRA used zero vectors and placed 3rd.

*When it would earn its place:* free-text preferences that don't map to fields ("somewhere with character"). Even then the fix is tagging at seed time, not embedding at query time.

**Live scraping.** Scrape to **seed**, before the event — that's what COBRA's `seed_from_apify.py` does. Never at query time. Freshness is invisible to a judge; a scrape failing on camera is not. And stale listings are our premise: if the data were fresh to the second, the product wouldn't need to exist.

**LangChain / LangGraph.** The reasoning here is: extract preferences (one structured call), extract outcome (one structured call), rank (pure code). There's no agentic loop to orchestrate — the voice provider runs the conversation. A graph abstraction over something that isn't a graph is overhead, not leverage.

**Also no:** auth of any kind (the session id in the URL is the access model) · websockets · Celery · monorepo tooling · CI/CD · state libraries (you have one polled object) · MUI/Chakra.

## Two things nobody remembers until 14:30

**Recording the phone screen.** The hero shot is a second camera filming a phone on speaker with the page visible. You'll also want a clean capture of the cards reshuffling: iPhone → Mac by cable, QuickTime → New Movie Recording → source = iPhone. **Test this before 14:00.**

**The architecture diagram.** Excalidraw, five minutes, export PNG, drop in the README. Judges reading a repo want one and almost nobody includes it.

## Known environment traps

**Intel Mac + `cryptography`.** Pinned `<47` in `pyproject.toml`. Releases after 46.0.3 ship no macOS x86_64 wheel, so uv falls back to building from Rust source, which fails on an older Cargo toolchain. It arrives transitively via `twilio` → `pyjwt[crypto]`. Hit and fixed at 3am; don't relax the pin.

**Python pinned to 3.12** in `.python-version`. uv otherwise picks 3.13, which widens the no-wheel problem.
