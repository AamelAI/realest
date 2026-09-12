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
