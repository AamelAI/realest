# Realest

**Which listings are actually real.**

> Every AI voice agent in real estate works for the brokerage. **Realest works for the renter** — you talk, a page in your hand reorders as you talk, and it phones the listing agents to find out the things no listing will ever tell you.

Built by **AAMEL** at *Agents, Everywhere: Bots, Channels & More* — Toronto, 12 September 2026.

---

## The problem

Toronto rental listings are wrong. Units are already leased, "parking included" turns out to be $180 on top, pet policy is anyone's guess. The bottleneck has never been *finding* listings — it's that half of what you find is dead or misleading, and the only way to know is to phone eight people and play tag for two days.

## What it does

You call the agent and say what you're after. It texts you a link, and a page in your hand fills with listings — photos, rent, beds, transit. Keep talking and it reorders as your priorities change.

Then it asks the question that makes it more than a search tool:

> *"Listings go stale fast. Want me to call the listing agents and check they're real? Anything else you want me to ask?"*

It calls them. One is already leased. One is $200/month more than listed once parking is in. One is available Saturday — cats only, and you mentioned a dog. **Your shortlist reorders, and every reason came from a human who answered a phone thirty seconds ago.**

If nobody picks up, or it's the wrong hour to be calling, it drafts an email instead and says so.

---

## Why this can't be a chatbox

1. **It phones third parties.** A chat window cannot.
2. **The deciding information exists nowhere online.** *Is it still available, what does parking really cost, will you take a dog* lives in a leasing agent's head until someone asks. No model, index or scrape retrieves it. **The agent creates the data by talking to a human.**
3. **Voice and screen are one live session.** You're on the phone while a page in your other hand reorders from the same agent state.

---

## A real call, in full

Placed at 13:53 on build day. Not scripted, not reconstructed — this is the transcript ElevenLabs returned from a real phone, answered by a person:

```
AI:    Hello, my name is Alex, and I'm an AI assistant calling on behalf of a
       renter. I'm calling about the listing at 155 Yorkville Avenue.
Agent: Hello.
AI:    Thank you for taking my call. I am inquiring about your rental listing
       and wanted to confirm if the unit is still available?
Agent: Uh, yes, it is available.
AI:    Great, thank you. Could you please tell me the exact monthly cost for
       parking, separate from the rent?
Agent: It's $200 per month.
AI:    Thank you, that is two hundred dollars per month. Could you also please
       clarify your pet policy for this unit?
Agent: Uh, no pet is allowed.
AI:    Understood, no pets are allowed. Finally, could you please let me know
       what viewing slots you have available for the renter?
```

Extracted into the typed schema the ranker consumes:

```json
{ "available": true,
  "addons": ["parking $200/month"],
  "pets_allowed": "no",
  "viewing_slot": "Friday at 2:00 p.m.",
  "source": "Agent" }
```

**Two facts no listing contained** — a $200 parking cost and a no-pets policy — and the real rent silently became $2,890 instead of $2,690. That is the entire product in one call.

## And the shortlist reordering

```
"two bedroom, Yorkville or the Annex, under $3,400. I've got a dog"
  1. 155 Yorkville Ave   $3,000
  2. 322 Dupont Street   $3,290
  3. 155 Yorkville Ave   $2,690
  4. 660 Huron Street    $2,290

"actually parking matters more than anything"      → reorders mid-sentence

"yes, call them all — and ask if there's a locker"
  1. 155 Yorkville Ave  verified   $2,690   cats only, no dogs · Saturday at two
  2. 660 Huron Street   no answer  $2,290   email drafted
  3. 322 Dupont Street  verified   $3,470   parking $180 — over budget
  4. 155 Yorkville Ave  dead       $3,000   leased Tuesday
```

The top pick dies and sinks to last. The second is $180 more than advertised. **The reorder is computed from phone calls, not from data.**

---

## What's real, and what isn't

We would rather tell you than have you find it in the source.

| | |
|---|---|
| **Real** | Inbound voice (ElevenLabs ConvAI on a Twilio number), outbound calls, `CallOutcome` extraction, ranking and re-ranking, the live page, SMS delivery, the email fallback |
| **Scripted** | The **recorded demo** runs `TRANSPORT=stub` — a scripted listing agent, so the take is clean and repeatable |
| **Seeded** | 104 Toronto listings scraped from rentals.ca before the event. Real addresses, rents and photos. `parking_included` and `pets` are deliberately synthesized — they are exactly the facts a listing doesn't state reliably, which is the premise |
| **Not built** | Real email sending — drafts are shown, never sent |

The stub mocks the **phone network**, not the product. Its transcripts go through the same `extract_outcome()`, the same schema and the same re-rank. Only the dial tone changes; `TRANSPORT=eleven` swaps in real calls and nothing else moves.

---

## Architecture

```
  caller's phone ──▶ ElevenLabs ConvAI ──webhook tools──▶ FastAPI
                            ▲                               │
                            │ outbound calls                ▼
                   listing agents' phones            SessionStore
                                                           │ poll 1.2s
                                                           ▼
                                                  Next.js page (Vercel)
```

One **session store** is the source of truth. Voice writes it through webhook tools; the page reads it by polling. They never talk to each other.

Every tool — voice or text — routes through one seam:

```python
dispatch(tool_name, args, session_id) -> str   # the line spoken back
```

That is why the whole product could be built and rehearsed by **typing** (`POST /chat`) while telephony landed in parallel.

**Ranking** is a pure function, synchronous and in-memory, because it runs while someone is mid-sentence. `DEAD` sinks to the bottom. Real rent — listed plus mandatory add-ons — replaces listed rent once a human corrects it. Verified outranks unverified. Neighbourhoods are fuzzy on purpose: exact match scores 30, a walkable neighbour 14, because a caller who says "King West" means "or near enough that I'd still go and see it."

### Stack

**OpenAI** structured outputs for `Preferences` and `CallOutcome` · **ElevenLabs ConvAI** for both call directions over a **Twilio** number · **Gemini** as the chat-path LLM · **Exa** for card enrichment · **Next.js 15** on Vercel · **FastAPI** · **ngrok**

---

## How it behaves around real people

- Identifies itself as an AI in the **first sentence** of every outbound call
- Calls only listings you selected. It never cold-dials
- Won't place calls outside business hours — it says so and offers email instead
- Every call-derived fact carries provenance on the card: *"parking $180 — Mark, 1:41pm"*
- **Never records a fact a human didn't say.** If they didn't mention pets, the field stays null
- No realtor contact details were scraped. Every number in the dataset is a teammate's, by design

---

## Prior art

The category exists — entirely on the other side of the table. **EliseAI, Funnel, Yardi Chat IQ, CloudTalk** and **Bland** all sell *inbound* lead capture to property managers: they answer the phone, qualify you, and book you into the brokerage's calendar.

Realest is the inverse. It represents the renter and dials outward. We could not find that shipped anywhere.

---

## Run it

```bash
cp .env.example .env          # fill in keys
make install                  # uv sync + npm install
make listings PHONE=+1416… EMAIL=you@example.com
make seed                     # validates every row
make dev                      # FastAPI :8000
make tunnel                   # ngrok — the voice webhooks need this
make web                      # Next.js :3000
make doctor                   # tells you what's still missing
```

Talk to it without a phone at **`localhost:8000/chat`** — same prompt, same tools, same `dispatch()`.

`TRANSPORT=stub` (default) scripts the listing agents. `TRANSPORT=eleven` dials for real.

---

## Built during the event

Everything in `server/`, `web/app`, `web/components` and the demo scripts was written between 11:15 and 15:30 on 12 September 2026.

Prepared beforehand and explicitly permitted as scaffolding: credentials, dependencies, empty module stubs, the scraped listings dataset, and the documentation in `docs/`. Every stub carried a `TODO(hackathon)` marker; none remain.

## Known limitations

- The recorded demo runs on the scripted transport. Real calls are proven but slower on camera — a live one took 131 seconds
- Add-on extraction is occasionally non-deterministic; a mumbled "two hundred a month" sometimes fails to parse into a figure
- Inbound needs the initiation webhook to mint a session; without it each tool call lands in its own session
- Listings are a dated snapshot, and the backend runs on a laptop behind a tunnel
- Emails are drafted and displayed, never sent

---

*Realest — it was hiding inside **real est**ate the whole time.*
