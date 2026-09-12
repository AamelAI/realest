# Written description — paste into the submission form

**Realest — which listings are actually real.**

Every AI voice agent in real estate today works for the brokerage. EliseAI, Funnel, Yardi Chat IQ, CloudTalk and Bland all sell the same thing: an inbound assistant that answers the phone, qualifies you as a lead, and books you into the agent's calendar. **Realest inverts that. It represents the renter, and it dials outward.**

## The problem

Toronto rental listings are wrong. Units are already leased, "parking included" turns out to be $180 extra, the pet policy is anyone's guess. Finding listings was never the bottleneck — knowing which ones are real is, and the only way to find out is to phone eight agents and play voicemail tag for two days.

## The environment, and why it is load-bearing

The agent lives **on the phone network**, in both directions. You call it, describe what you want, and it texts you a live link while you are still talking. You keep talking; the page in your hand reorders as your priorities change. Then it asks the question that makes it more than a search tool — *"Listings go stale fast. Want me to call the listing agents and check? Anything else you want me to ask?"* — and it calls them.

Three claims that a chat window cannot meet:

1. **It phones third parties.** A chatbot cannot place a call to a human being.
2. **The deciding information exists nowhere online.** *Is it still available, what does parking actually cost, will you take a dog* lives in a leasing agent's head until somebody asks. No model, index or scrape can retrieve it. The agent **creates** that data by talking to a person.
3. **Voice and screen are one live session.** You are speaking on the phone while a second surface in your other hand re-renders from the same agent state. Not a transcript, not a web app — one conversation rendered twice, each channel doing what it is good at.

The environment does not decorate the workflow; it *is* the workflow. The ranking is not computed from a dataset. It is computed from phone calls placed to humans thirty seconds earlier.

## What that looks like

A real call placed during the build, to a real person:

> **AI:** Hello, my name is Alex, and I'm an AI assistant calling on behalf of a renter, about the listing at 155 Yorkville Avenue… could you tell me the exact monthly cost for parking, separate from the rent?
> **Agent:** It's $200 per month.
> **AI:** …and could you clarify your pet policy for this unit?
> **Agent:** Uh, no pet is allowed.

Two facts that appear in no listing. The rent silently becomes $2,890 instead of $2,690, the unit is disqualified for a renter with a dog, and the shortlist reorders — with the reason, and the name of the person who said it, printed on the card.

In the full flow the top-ranked listing turns out to have been leased on Tuesday and sinks to last; a second is $180/month more than advertised once parking is included, pushing it over budget; a third does not answer, so the agent drafts an email instead; the fourth books a viewing for Saturday at two — and is cats-only.

## Technical execution

**Voice** — ElevenLabs Conversational AI on a Twilio number carries both directions. Inbound, a conversation-initiation webhook mints one session id for the whole call and captures the caller's number; without it every webhook tool would land in its own session. Outbound, the agent identifies itself as an AI in its first sentence, asks the caller's own extra questions, and reports back.

**Reasoning** — OpenAI structured outputs parse free speech into two typed schemas: `Preferences` from the renter, and `CallOutcome` from each listing agent. `CallOutcome` is what turns a transcript into something rankable. The extractor is instructed never to fill a field the human did not say; if pets were not mentioned, the field stays null. A hallucinated fact would destroy the only claim the product rests on.

**Architecture** — a single in-memory session store is the source of truth. Voice writes it through webhook tools; the Next.js page reads it by polling every 1.2 seconds. The two never talk to each other. Every tool, voice or text, routes through one seam — `dispatch(tool_name, args, session_id)` — which is why the entire product could be built and rehearsed by typing at `POST /chat` while telephony landed in parallel, and why swapping the call transport changes one environment variable and nothing else.

**Ranking** is a pure synchronous function, because it runs while somebody is mid-sentence and a network hop there is dead air. Dead listings sink. Real rent (listed plus mandatory add-ons) replaces listed rent the moment a human corrects it. Verified outranks unverified. Neighbourhoods are deliberately fuzzy — an exact area match scores 30, a walkable neighbour 14 — because a caller who says "King West" means "or near enough that I would still go and see it," and strict matching returns an empty shortlist.

**Stack** — ElevenLabs ConvAI · Twilio Voice + SMS · OpenAI structured outputs · Gemini (chat path) · Exa for card enrichment · FastAPI + Pydantic · Next.js 15, Tailwind 4, Framer Motion on Vercel · ngrok.

## Usefulness and control

Everyone who has hunted for an apartment has taken a streetcar across town to see a unit that was leased on Tuesday. There is no explanation tax on this problem.

The agent stays controllable throughout. It asks *"anything else you want me to ask?"* before it calls, so you brief your representative before it speaks for you. It calls only the listings you selected and never cold-dials. It identifies itself as an AI in the first sentence of every call. It refuses to dial outside business hours and offers email instead — judgment about human norms, not a retry. Every fact it learned carries provenance on the card: *"parking $180 — Mark, 1:41pm."* And when a hard conflict appears — cats only, and you have a dog — it surfaces the conflict rather than silently dropping the listing. The person decides.

## What is real, and what is not

We would rather say it than have it found in the source. Inbound voice, outbound calls, extraction, ranking, the live page and SMS delivery are all real and were exercised on real phones during the event. The **recorded demo** runs on a scripted call transport so the take is clean and repeatable; that stub mocks the phone network, not the product — its transcripts pass through the same extraction, the same schema and the same re-rank. Listings are a dated snapshot of 104 real Toronto rentals with real addresses, rents and photos. No realtor contact details were ever scraped; every number in the dataset belongs to a teammate, by design. Emails are drafted and displayed, never sent.

**Repo:** https://github.com/AamelAI/realest

---

## Notes for whoever finalizes this (D2)

- **CopilotKit**: named per the required tag list; we evaluated it and didn't
  end up using it (`docs/SPONSORS.md` documents this decision) — the social
  post below should stay honest about that rather than imply we did.
- **The number**: the written description above doesn't invent a measured
  "X minutes → Y seconds" stat — the `submit` skill is explicit that a
  fabricated number costs more credibility than it buys. If someone times a
  real call before submission, add it here.

## Social post

> 🏠 **Realest** — every AI voice agent in real estate works for the
> brokerage. Ours works for the renter.
>
> You call it, describe what you want, and it texts you a live link while
> you're still talking. It calls listing agents **in parallel** to find out
> what no listing tells you — still available? real cost with every add-on?
> pets? — and reorders your shortlist live from what it just learned.
>
> Built at Agents, Everywhere (Toronto) for AI Tinkerers and Human Feedback
> Foundation, hosted by Georgian. Voice runs on **@ElevenLabs** over Twilio;
> reasoning and extraction on **@OpenAI**, provider-agnostic through
> **@OpenRouter**. Explored **@CopilotKit** for the live page and shipped
> plain React + polling instead so the demo can't drop mid-call.
>
> #AgentsEverywhere #AITinkerers

---

## Final submission checklist (`7.1`–`7.5`)

Status as of the last `make todo` run plus the latest merged main. Nobody
should have to reconstruct this from `.claude/skills/submit/` under time
pressure at 15:00 — check these five off in order, don't submit until all
five are real.

| # | Item | Task | Owner | Status |
|---|---|---|---|---|
| 1 | Project title | — | — | ✅ Done — **Realest** |
| 2 | Written description | `7.1` (README) + `7.3` (description) | D1 / D2 | ✅ Finalized — inbound/outbound voice confirmed working, claims match the current build |
| 3 | Public GitHub repo URL | `0.5` + `7.4` | D1 / D4 | 🟡 Description above cites `https://github.com/AamelAI/realest` — verify it's actually public and loads signed out (`7.4`) before relying on this |
| 4 | Two-minute demo video | `7.2` | D3 | 🔴 Not started as of this check |
| 5 | Social post (tag OpenAI, Georgian, CopilotKit, OpenRouter, AI Tinkerers, Human Feedback Foundation) | `7.3` | D2 (me) | ✅ Finalized above, all six tagged — **not posted externally yet** |

**Repo hygiene** (`.claude/skills/submit/`'s own checklist) — clean as of the last check:
- ✅ Commit history real and dated today
- ✅ No leaked secrets (working tree and full git history)
- ✅ `.env` gitignored, never committed; `.env.example` current
- ✅ No absolute laptop paths in tracked files
- ✅ README setup commands all exist in the Makefile
- ⬜ "Repo is public" — re-verify on `AamelAI/realest` itself as part of `7.4`
