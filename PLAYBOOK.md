# Realest — Build Playbook

**Agents, Everywhere · Toronto · Georgian · build day** · by **AAMEL** (عامل — "the one who acts")

> **Realest — which listings are actually real.**

Listings lie. Realest calls and finds out.

*The name is hiding inside the category: **REAL EST**(ATE). Don't explain it in the title — save it for the video's closing card and let the judge find it.*

A voice agent that represents the renter instead of the brokerage. You talk; a page in your hand reshuffles as you talk. It phones three listing agents at once, learns what no listing says, and reorders your shortlist from what humans told it — falling back to email when it's the wrong hour to call.

| | |
|---|---|
| **Build window** | 11:15–15:30 |
| **Feature freeze** | 14:30 |
| **Submit by** | 16:00 |
| **Cities** | 48 |
| **Registered** | 5,648 |

---

## 1. The read

### The one fact that changes everything

**Nobody judging this will watch your demo.** Toronto's afternoon show-and-tell is explicitly non-judged — every city feeds one global pool. Judges score from four artifacts: title, written description, public GitHub repo, and a two-minute video.

The deliverable is not "a working agent." It's **a repo and a video that prove one**.

| | |
|---|---|
| **Real build time** | Schedule says 11:15–15:30, but the video has to be shot, cut and uploaded. **Feature freeze at 14:30.** That is ~3h15m of building. |
| **The field** | 48 cities, 5,648 registered. The May 2026 Generative UI global ran to roughly 200 projects across ~20 cities; at 48, expect the high hundreds. |
| **The trap** | The rubric scores "the environment mostly serves as a wrapper" a **2 out of 5**. Voice will be one of the biggest clusters today. A voice search assistant *is* a wrapper. The outbound calls are not. |
| **Eligibility** | Core functionality must be built during the event; templates, libraries, starter code and **seeded demo data are explicitly allowed**. Be ready to say which is which. |

---

## 2. The rubric, decoded

Four criteria, 1–5 each, scored by global judges after submissions close.

### Core Requirements & Functionality

> "Robust, reliable, and fully functional within its intended environment."

One rehearsed path: call in, page out, three calls, reshuffle, booking, SMS.

### Innovation & Theme Alignment

> "Reveals a surprising new agent pattern whose central value **could not be reproduced in a standalone chatbox**."

**THE WHOLE GAME.** Voice and screen are one live session, and the deciding information existed in no dataset until a human said it aloud.

### Technical Execution & Integration

> "Robust orchestration, **thoughtful failure handling**, and a deeply integrated architecture."

Three concurrent realtime sessions, one shared session store driving two channels, per-call timeouts, and channel-switching to email when calling is wrong.

### Usefulness & Agentic Experience

> "Using context intelligently **while remaining clear and controllable**."

You brief it before it calls, you tap which calls to make, and you see everything it learned and from whom.

---

## 3. What has actually won

From four recent AI Tinkerers podiums — Toronto (Sep 2025), New York (Feb 2026), Poland (Mar 2026), Generative UI global (May 2026).

**Voice plus a live link is a proven podium shape.** Call someone, text them a link, update that page live during the conversation.
→ *SITE COBRA* — 3rd, Poland. Called business owners, texted a live demo link, updated the page from spoken feedback mid-call.

**One loop, done well.** Winners were single loops. Multi-agent systems won only when the orchestration itself was on camera.
→ *Agent-Mon* — 2nd, NYC, in its own words: "Stability comes from radical simplicity… no bundler, no framework, no build step."

**They named their competitor.** Prior art never disqualified anyone. Winners cited the incumbent on purpose — it reads as market awareness.
→ */shipit* pitched itself as "Cursor for design." *Recordly* called its output "indistinguishable from a Screen Studio demo."

**One concrete number.** Every winner quantified the before/after.
→ *GameSight* $50,000 playtest → ~$3. */shipit* 15 min → 5 min.

---

## 4. The project

### The problem nobody is solving

Toronto rental listings are wrong. Units are already leased, "parking included" means a $180 add-on, the photos are two tenants old, pet policy is anyone's guess. The bottleneck has never been *finding* listings — it's that half of what you find is dead or misleading, and the only way to know is to phone eight people and play tag for two days.

### The inversion — your pitch's first line

> Every AI voice agent in real estate today works for the brokerage. It answers the phone, qualifies you as a lead, and books you into *their* calendar. Realest works for the renter. It makes the calls instead of receiving them.

EliseAI, Funnel, Yardi Chat IQ, CloudTalk, Bland and a dozen others all sell inbound lead capture to property managers. The renter-side agent that dials outward isn't a shipped product anywhere. Name them in the README and state the delta — winners did exactly this.

### Three reasons it cannot be a chatbox

1. **It phones third parties.** A chat window cannot do this. Full stop.
2. **The deciding information exists nowhere online.** "Is it still available, what does parking really cost, will you take a dog" lives in a leasing agent's head until someone asks. No model, no index, no scrape retrieves it. The agent *creates* the data by talking to a human.
3. **Two channels, one session.** You're speaking on the phone while a page in your other hand reorders itself from the same agent state. Not a chat transcript, not a web app — one conversation rendered twice, each doing what it's good at.

### The second screen — why this is the upgrade, not a feature

Voice is invisible. That was the single biggest weakness in this build: a judge watching forty videos cannot *see* a shortlist reorder inside an audio stream. The page fixes that — but not as a dashboard built for judges. It's a surface the user genuinely needs, because nobody chooses an apartment without seeing the photos.

It earns three things at once: voice handles what voice is good at (open-ended preference, nuance, interruption), the screen handles what screens are good at (images, comparison, precise multi-select), and tapping three checkboxes is far more reliable than parsing *"yeah do the first and the third one"* out of a phone call.

> And it makes CopilotKit load-bearing. A page whose contents are assembled from streaming agent state is exactly what AG-UI exists for — which moves Best Use of CopilotKit from a long shot to a real target.

### Channel judgment, not a fallback

If a realtor doesn't pick up, or it's 9pm on a Saturday, the agent doesn't fail and it doesn't blindly dial. It says so:

> *"It's after seven — I'd rather not cold-call them now. I can email all three tonight and text you when they reply, or try first thing Monday."*

Frame this as the agent reasoning about human norms, because that's what it is — and "thoughtful failure handling" is named in criterion 3's top band. Most teams will show a retry. Almost none will show an agent that declines to act because the timing would be rude.

### The single loop

Talk → shortlist appears on your phone → brief the agent → tap which to call → three parallel calls → **the page reshuffles from what they said** → book → SMS.

Everything else is cut.

---

## 5. The demo scenario

Your pitch, your video storyboard and your rehearsal script. Run it until the call takes 90 seconds.

> **Realest:** "Hi — I'm an AI assistant that finds rentals in Toronto and calls the listing agents for you. What are you after?"
>
> **Caller:** "Two-bedroom condo, King West or Liberty Village, under $3,400, and I need parking."
>
> **Realest:** "Four fit. I've just texted you a link — have a look while we talk."
>
> *[Camera: phone on speaker in one hand. The link opens. Four cards with photos, rent, beds, baths, pets, amenities.]*

### Your phone · before (00:38)

| # | Listing | Specs | Notes |
|---|---|---|---|
| 1 | Strachan Ave | $3,180 · 2 bed · 1 bath · parking incl. | 4 min to King streetcar · gym, roof deck |
| 2 | Wellington St W | $3,250 · 2 bed · 2 bath · parking incl. | 8 min to King streetcar · concierge |
| 3 | Bathurst St | $3,390 · 2 bed · 1 bath · no parking | 11 min to streetcar · pets OK |
| 4 | Lynn Williams St | $3,295 · 2 bed · 2 bath · parking incl. | 3 min to Exhibition GO · locker, gym |

> **Caller:** "Honestly, being near the streetcar matters more than parking."
>
> ⚡ *[Screen: the cards reorder while he's still speaking. No refresh, no tap.]*
>
> ⚡ **Realest:** "Before you pick — listings go stale fast. I can call the listing agents right now and check they're real. I'll ask availability, what parking actually costs, and pets. **Anything else you want me to ask?**"
>
> **Caller:** "Ask if there's a locker."
>
> **Realest:** "Tap the ones you want me to call."
>
> *[Screen: three checkboxes tapped. Three outbound calls fire at once; each card flips to "calling…" with a live timer.]*

### Your phone · after the calls (01:24)

| # | Listing | Status | What the call revealed |
|---|---|---|---|
| 1 | Lynn Williams St | **Verified · booked** | $3,295 · locker incl. · cats only · Sat 2:00pm confirmed |
| 2 | Wellington St W | **Price wrong** | $3,430 real — +$180 parking, +$40 locker. Over budget |
| 3 | Bathurst St | **No answer** | Email drafted — tap to send |
| 4 | ~~Strachan Ave~~ | **Dead** | Leased Tuesday. Listing never pulled down |

> ⚡ **Realest:** "Your top pick is gone — leased Tuesday, the listing is stale. Wellington is really $3,430 once parking and a locker are in, which puts it over budget. Bathurst didn't pick up, so I've drafted an email — it's on your screen. Lynn Williams is available, locker included, Saturday at two. **One catch: cats only, and you mentioned a dog.**"
>
> **Caller:** "Take Saturday at two. I'll sort the dog out."
>
> *[Camera: card turns green. A second later the phone buzzes with the SMS.]*

### Shoot it in one take, one hand

Phone on speakerphone, held in frame, page visible. You hear the agent and watch the cards reorder in the **same shot** — that single frame is the entire argument for why this isn't a chatbox, and it's worth more than any architecture slide.

Five details carry the submission:

- the cards reordering *while he's still talking*
- "anything else you want me to ask?"
- the agent catching a $180 lie
- "cats only, and you mentioned a dog" (context carried across two separate phone calls)
- the email draft appearing when nobody picked up

### Do this ethically, and say so

A teammate holds the realtor's phone. Same footage, nobody's workday interrupted. Then pre-empt the obvious objection in one README line:

> The agent identifies itself as an AI in its first sentence, calls only listings you tapped, never cold-dials, and won't call outside business hours.

That converts a skeptic's question into criterion-4 evidence.

---

## 6. Build order — do not reorder this

The second screen is the right call and it is also exactly how teams ship nothing. This ladder exists so that if you stop at any rung, you still have a submission. Each one is demoable alone.

| # | Rung | Detail | |
|---|---|---|---|
| 1 | Voice in, shortlist, voice out | The whole loop works with zero web. If nothing else lands, this is still a project. | **Shippable** |
| 2 | SMS a link to a static page | Server-rendered shortlist with photos. No live sync yet. Fifteen minutes. | **Shippable** |
| 3 | One outbound call, result lands on the page | Refresh to see it. The minimum version of the whole idea. | **Shippable** |
| 4 | Live sync — poll every second | Not websockets. A 1s poll against `/session/:id` gives the full visual reshuffle at a fraction of the risk. **The money shot.** | **Shippable** |
| 5 | Tap-to-confirm which calls to make | More reliable than parsing multi-select out of speech, and it's your approval gate. | **Shippable** |
| 6 | Email fallback + hour-of-day judgment | Draft it, show it on the page, one tap to send. Don't build SMTP plumbing. | *If ahead* |
| 7 | Three calls in parallel | The human-impossible beat — but a clean two-call demo beats a broken three-call one. Make one call perfect first. | *If ahead* |

### Design rule

**The page must never be load-bearing for the voice loop.** If the poll dies or the phone locks, the agent still completes the call, still books, still texts. Build the page as an enhancement on a working conversation, not as a dependency — correct engineering, and demo insurance.

---

## 7. Architecture and the sponsor stack

One session store is the single source of truth; voice and screen are two renderings of it. Say exactly which sponsor feature you used and why — that sentence is what a "best use of X" judge reads.

| Component | Use | |
|---|---|---|
| **Session store** | In-memory object keyed by `CallSid`, holding preferences, ranked listings, and per-call outcomes. The voice agent writes it; the page reads it. **Everything else hangs off this.** Build it first and both channels stay in sync for free. | Core |
| **OpenAI** | Realtime API for the inbound session and every outbound agent. Structured outputs for `Preferences` and `CallOutcome` — the second schema is what makes call results rankable instead of just transcribed. | Core |
| **Twilio** | Number, media streams in, outbound dial, and the SMS that carries the link. Not a sponsor — the handbook says use any stack. | Core |
| **CopilotKit** | The page. Cards assembled from streaming agent state is precisely what AG-UI is for, and it puts you in the running for the named award. **Judgement call:** if nobody is already fluent in it, build the page with plain React + a 1s poll and forget the award — don't let award-chasing sink the build. | Core |
| **Trigger.dev** | Fans out the concurrent calls with per-call timeouts, returns partial results when one agent doesn't answer, and owns the retry/escalate-to-email decision. Genuinely load-bearing, and its run trace is good README material. | Core |
| **Exa** | Enrich the cards with what listings omit — transit times, building reputation, neighbourhood context. Fetch while the user is still talking so the page fills in as they read. Exa credits ride on all three podium places. | Core |
| **OpenRouter** | Gateway for non-voice reasoning (ranking rationale, call summarization, email drafting) with a preset fallback chain. Cheapest route to criterion 3's "thoughtful failure handling." | Core |
| **Auth0** | Skip. The page is now your approval surface — tapping a card is better controllability than a push notification, and costs nothing extra. | Skip |
| **Ambiguous AI** | Write the verified shortlist as a Doc and the viewing as a Calendar entry — a ~20-minute lottery ticket on the DGX Spark after 13:30. Won't win the category without more breadth. | If ahead |
| **Cloud Run** | Skip for the demo. You need a long-running websocket process; scale-to-zero kills live sessions. Tunnel from a laptop. | Skip |

### Gotchas that eat hours

- **Audio format.** Twilio media streams are base64 G.711 μ-law at 8kHz. Set Realtime's input and output format explicitly. Mismatch produces silence or static and an hour of confused debugging.
- **Barge-in.** On `speech_started`, clear Twilio's queued audio or the agent talks over the interruption. The single most common voice-demo killer.
- **Never block speech on a network call.** Rank in memory. Pre-fetch Exa. Dead air reads as broken.
- **Poll, don't socket.** A 1s poll is visually identical to streaming at this scale and cannot drop mid-demo.
- **Session token in the link.** `/s/<random>`, no auth, expires with the session. Don't build login.
- **Concurrency.** Three simultaneous outbound calls may need more than one Twilio number. Test before 12:30, not at 14:00.
- **Booking is plain code.** The model calls `book_viewing(listing_id, slot)`; the function does the write. Models improvising state changes is how live demos fail.
- **Seed 50 listings with photos.** Use stock interiors and say so in the README — don't pass brokerage photos off as your own. Every contact number is your teammate's phone.

---

## 8. Who owns what

Split by layer. The page changed this balance — Dev 3 now owns a real product surface, so the page spec must stay small enough that they finish by 13:30 and switch to artifacts.

### Dev 1 — the ear + the store

Session store first (everything depends on it), then Twilio inbound, Realtime session, barge-in, live preference extraction, the re-rank, and the closing summary the agent speaks. Writes the README at 14:30 — they know the architecture.

*Test: a natural 60-second conversation with no dead air, and the store reflects every turn.*

### Dev 2 — the second line

Outbound dialling, the realtor-facing agent and its question script, `CallOutcome` extraction, Trigger.dev fan-out with timeouts, the hour-of-day check, email drafting, SMS.

*Test: three calls fire at once and return structured results — including one no-answer that becomes a drafted email.*

### Dev 3 — the page

Seed 50 listings with photos, the ranking function, then the page: one screen, card list, three states, mobile-first. No routing, no auth, no polish beyond the phone. Owns the video from 14:30.

*Test: open the link on a real phone, watch it reorder while someone talks.*

> **The cost of the second screen.** Dev 3 was going to own submission artifacts from 13:30. They can't now. **Artifacts become a hard whole-team stop at 14:30**, README on Dev 1, video on Dev 3. If the page isn't done by 13:30, freeze it at whatever rung it reached and move to artifacts anyway.

---

## 9. The day

| Time | What | Detail |
|---|---|---|
| **Before** | Keys, tunnel, seed data | Twilio number and a public HTTPS tunnel working. Keys in `.env`. 50 Toronto listings in SQLite *with photo URLs*, realistic agent names, teammate's phone as every contact. Repo scaffolded. All explicitly permitted. |
| 10:30 | Opening broadcast | One person listens for rubric changes and the starter repo. The other two start the audio spike. |
| **11:15** | **Gate 1 — locked, no debate after this** | Agree the session-store shape in five minutes. Both other lanes depend on it. |
| 11:15 | Three lanes, each proving one unknown | Dev 1: can you hear the agent. Dev 2: can it dial out. Dev 3: seed data, ranking, static page. Nothing else. |
| **12:30** | **Gate 2 — audio in AND dial out, or fall back** | If telephony isn't working, switch the inbound leg to browser-mic Realtime and keep the outbound calls. The outbound leg is the part worth saving. |
| 12:30 | Climb the ladder, ugly | Rungs 1–4 in order. Do not start rung 5 until rung 4 works. |
| **13:30** | **Gate 3 — one conversation ends in a booking, with the page live** | If not, freeze the ladder where it is. A smaller thing that works outscores a bigger thing that doesn't on all four criteria. |
| 13:30 | Harden and rehearse | The no-answer path on camera. Then run the script end to end at least three times — you're rehearsing a performance, not testing software. |
| **14:30** | **FEATURE FREEZE — whole team on artifacts** | Nothing built after this reaches a judge. |
| 14:30 | Record — multiple takes | Never ship the first take of a live phone call. Shoot three, cut the best. Keep a clean backup from 14:00. |
| 15:10 | Submit | Title, description, public repo, two-minute video, social post tagging OpenAI, Georgian, CopilotKit, OpenRouter, AI Tinkerers, Human Feedback Foundation. Assign the post to a person. |

---

## 10. Scored as if finished

Honest projection if you execute the spec — not the optimistic one.

### Core Requirements & Functionality — **4 / 5**

The loop is complete and the environment is real. Live telephony built in three hours has edges, and now there are more moving parts. What saves it is that the page gives a judge something to *look at* while the audio plays, so the same build reads as more finished than it would have.

*To reach 5: rehearse three times before recording, and make sure the voice loop completes even if the page dies. Cheapest whole point available today.*

### Innovation & Theme Alignment — **5 / 5**

Three independent un-chatboxable claims now: it phones third parties, the deciding information existed in no dataset, and voice plus screen are one live session. The shortlist inverting mid-call is exactly the rubric's "surprising new agent pattern."

*Drops to 3 if your description opens with "a voice assistant for apartment hunting." Open with the inversion.*

### Technical Execution & Integration — **5 / 5** *(moved 4 → 5)*

One session store driving two synchronized channels, three concurrent realtime sessions, structured call extraction, and channel-switching to email on timeout or hour-of-day is "deeply integrated architecture" by any reading — and the email path is failure handling that shows judgment rather than a retry.

*To hold 5: the no-answer → email beat must be on camera, and the README needs the architecture diagram plus both call transcripts.*

### Usefulness & Agentic Experience — **5 / 5**

Every judge has hunted for an apartment and been burned by a stale listing — zero explanation tax. Each channel does what it's good at, you brief the agent before it represents you, you tap what it's allowed to do, and you see what it learned and from whom.

*Holds at 5 if you keep "anything else you want me to ask?" — the cheapest controllability evidence in the build.*

### **Projected if executed as specified: 19 / 20**

> **The honest version.** 19 is the *spec*, not the forecast. Realistic for a first telephony build is **16–17**, and the scope you just added widens the gap rather than narrowing it — more surface, more to go wrong, one fewer person on artifacts. The ladder in §6 is what converts the upside into a score instead of a story about what you almost built. **Climb it in order and freeze without guilt.**

### What would still make it better

- **Put a number on it.** Time yourselves phoning three listing agents by hand — realistically twenty minutes of hold music and voicemail. "Twenty minutes of phone tag, or ninety seconds." Measure it honestly; don't invent a stale-listing statistic you can't support.
- **Show a per-card provenance line.** "Parking $180 — from Mark at 1:42pm." Attribution turns the page from a UI into evidence, and it costs one field on `CallOutcome`.
- **Name your competitors in the README.** EliseAI, Funnel, CloudTalk, Bland — then the one-line delta. Winners did exactly this.
- **Let the agent decline once.** If the user asks it to call at 10pm and it says no and offers email instead, that's a 10-second beat almost no other submission will contain.

---

## 11. The submission is the product

### README — in this order

1. One-line hook: the inversion. Then a 20-second GIF of the page reshuffling.
2. **Both call transcripts, in full.** A judge reading your repo cannot hear your product.
3. Architecture diagram — one session store, two channels.
4. Prior art named, plus your one-line delta.
5. The ethics line: discloses AI, only listings you tapped, never cold-dials, no calls outside business hours.
6. What's real vs seeded — listings are a dated snapshot with stock photos, and say so.
7. Built today vs. from templates. Answer it before you're asked.

### Video — 120 seconds

| Time | Shot |
|---|---|
| 0:00 | Cold open: "Your top pick is gone — leased Tuesday." Card goes red on screen. No title card. |
| 0:12 | Rewind — preferences spoken, link arrives, cards appear with photos. |
| 0:30 | The reorder while he's still speaking. One hand, one shot. |
| 0:45 | "Anything else you want me to ask?" → tap three → calls fire. |
| 1:05 | Cards resolving live: dead, price wrong, no answer → email drafted. |
| 1:25 | The reshuffle and the dog line. Booking. Phone buzzes. |
| 1:45 | Architecture card, ten seconds. Then the number. |
| 1:55 | Closing card: **REAL EST**ATE → **REALEST**. Let it land without narration. |

### Description — first sentence

> "Every AI voice agent in real estate works for the brokerage. Realest works for the renter — you talk, a page in your hand reorders as you talk, and it phones three listing agents at once to find out which listings are actually real."

Then stack, then the number, then limitations. Judges read dozens of these; sentence one decides how carefully they read the rest.

---

## 12. Ways this loses

1. **The page becomes a dependency.** If a dropped poll can break the demo, you've built a liability. Voice completes the loop alone; the page is an enhancement.
2. **Websockets instead of polling.** A 1s poll looks identical on video and cannot fail mid-take. Save the hour.
3. **Presenting it as a voice search assistant.** That's the wrapper the rubric scores a 2, and it's the biggest cluster today. The calls are the product; the search is setup.
4. **Live scraping on camera.** Seed the listings. A scrape that fails during the demo takes functionality to 2 with no recovery.
5. **Building the PDF.** The page already is the shortlist. The PDF adds nothing a judge scores.
6. **Shipping the first take.** Live calls stumble. Three takes minimum, plus a clean backup from 14:00.
7. **No visible failure.** Let one realtor not answer, on camera, and let the agent switch to email gracefully.
8. **Forgetting the social post.** One of five required items, ninety seconds of work. Assign it to a person.

---

*Compiled from the Toronto event page, the hackathon portal rubric and handbook, and winner showcases from Toronto (Sep 2025), New York (Feb 2026), Poland (Mar 2026) and the Generative UI global (May 2026). Prior-art landscape from vendor and trade sources.*

*The organizers note the rubric may be updated before build day — confirm at the 10:30 briefing.*
