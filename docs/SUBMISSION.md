# Submission draft — task `7.3`

Written description and social post for the five required submission items
(`.claude/skills/submit/`). Not posted anywhere yet — review, then hand off
to whoever submits the form and posts.

Written against the repo as it stands right now: the full preference →
shortlist → parallel verification → structured outcome → re-rank → booking
loop is built and verified (`tests/`, all passing) over the text/stub
transport. Real inbound/outbound telephony (Step 4 in `TODO.md`) has not
landed yet, so nothing below claims a phone has actually rung. Update the
"what's built" section once voice is live and re-check every claim before
the real submission — don't just reuse this unedited.

---

## Written description

Every AI voice agent in real estate today works for the brokerage — it
answers the phone, qualifies the caller as a lead, and books them into the
property manager's calendar. **Realest** inverts that. It represents the
renter, and it's the one making the calls.

**How it works.** You describe what you're after — beds, area, budget,
parking, pets — and a live shortlist builds on a page in your hand,
reordering as you refine what matters most. When you're ready, you pick
which listings to verify and Realest calls those listing agents **at once**,
asking the three things a listing never says: is it actually still
available, what does parking really cost once every add-on is in, and will
they take a dog. Every answer is extracted into a structured fact with who
said it and when attached, and the instant one call lands, the whole
shortlist re-ranks from it — a top pick that's already leased sinks to the
bottom, a unit whose real cost is $180 over budget demotes below a cheaper
verified one, and a hard conflict (cats-only vs. your dog) is flagged rather
than silently dropped, because that's your call to make, not the agent's.
Booking is plain code, never a model improvising a state change, and a
confirmation follows by text. If a listing agent doesn't pick up, or it's
the wrong hour to be cold-calling someone, Realest declines to dial and
drafts an email instead of pretending the call went fine.

**Why this can't be a chatbox.** It phones third parties — a chat window
cannot. The deciding information (still available? real cost? pets?) exists
nowhere online; it lives in a leasing agent's head until Realest asks, so
the agent *creates* the data instead of retrieving it. And voice and screen
are designed as one live session, not a transcript and not a static web
app — the same conversation rendered twice, each channel doing what it's
good at.

**Stack.** OpenAI structured outputs drive every extraction step —
turning a call transcript into a typed, rankable fact instead of a wall of
text a human still has to read. That extraction path is provider-agnostic
by design: the same code runs unmodified against OpenAI, OpenRouter, or
Gemini, whichever key is configured, verified live against all of the
above. The live page is a polled Next.js surface reading one shared session
store — no sockets, so a dropped connection can't break a demo. Telephony
is designed to run on OpenAI Realtime over Twilio Media Streams; that leg is
still being wired in as of this draft (see "What's verified" below).

**What's verified right now.** The complete reasoning and orchestration
loop — preference extraction, parallel outbound verification (three calls
complete in the time one would, because they run concurrently, not in
sequence), structured outcome extraction, the re-rank, business-hours
judgment with an email fallback, and the booking write — is built and has
an automated test suite that passes end to end, exercised over a scripted
call transport and validated live against a real Gemini extraction call.
The live page renders real session state and reorders as it polls. Real
phone telephony (a caller actually ringing in, real outbound dialling to a
listing agent) is the piece still being connected; the entire agent logic
behind it is the same code that will run once it is.

**Limitations.** Listings are a dated snapshot, not a live feed, and we say
so rather than imply otherwise. Every outbound number in the demo dataset is
a teammate's own phone — Realest never cold-calls a real listing agent.
Voice telephony is in progress, not yet demonstrated end to end, at the time
of this draft.

---

## Social post

> 🏠 **Realest** — every AI voice agent in real estate works for the
> brokerage. Ours works for the renter.
>
> You tell it what you're after. It calls listing agents **in parallel** to
> find out what no listing tells you — still available? real cost with
> every add-on? pets? — and reorders your shortlist live from what it just
> learned, on a page in your hand.
>
> Built at Agents, Everywhere (Toronto) for AI Tinkerers and Human Feedback
> Foundation, hosted by Georgian. Structured extraction and reasoning run on
> **@OpenAI**, provider-agnostic through **@OpenRouter**. Explored
> **@CopilotKit** for the live page and shipped plain React + polling
> instead so the demo can't drop mid-call — the right trade for us today.
>
> #AgentsEverywhere #AITinkerers

---

## Notes for whoever finalizes this

- **CopilotKit**: named per the required tag list, but the description is
  honest that we evaluated it and didn't end up using it (`docs/SPONSORS.md`
  documents this decision already) — don't let the social post imply
  otherwise.
- **The number**: deliberately not claiming a measured "X minutes → Y
  seconds" stat — nobody has timed a real call yet. If someone does before
  submission, add it; the `submit` skill is explicit that a fabricated
  number costs more credibility than it buys.
- Re-verify the "What's verified" section against `make todo` right before
  submitting — if Step 4 (voice) lands, this whole section should be
  rewritten to lead with the live call, not the stub.
