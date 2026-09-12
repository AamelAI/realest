# Sponsor tools — what to reach for

Every sponsor at *Agents, Everywhere*, what it's actually good for, and whether we're using it. The handbook says **you don't need to use every tool** — pick what makes the project better.

Two named category awards exist and both have far smaller fields than the podium:

- **Best Use of CopilotKit** — purple AirPods Max per member
- **Best Use of Ambiguous AI** — one NVIDIA DGX Spark *(highest-value single item on the board)*

---

## Using — core to the build

### OpenAI · marquee sponsor
Our reasoning layer, and it should stay genuinely central even though telephony transport is managed.

- **Agents SDK** (`openai-agents`) — tool loops, handoffs
- **Structured outputs** — `Preferences` and `CallOutcome`. `CallOutcome` is what turns a transcript into something *rankable*. This is the most important single use of OpenAI in the project
- **Realtime API** — **carries every call.** Twilio Media Streams proxies audio both ways through `scripts/spike_bridge.py`. Chosen over a third-party voice vendor because it's the marquee sponsor, the event supplies credits, and it costs us nothing

→ [Agents SDK quickstart](https://openai.github.io/openai-agents-python/) · [Voice agents quickstart](https://platform.openai.com/docs/guides/voice-agents)

**README line:** *"Every call runs on the OpenAI Realtime API over Twilio Media Streams; Agents SDK and structured outputs drive preference extraction, call-outcome extraction, ranking rationale and email drafting."* That is a genuinely deep marquee-sponsor integration, not a logo drop.

### OpenRouter
One API across hundreds of models with automatic fallback. Our cheapest route to the rubric's **"thoughtful failure handling."**

- Put the model order in a **preset** — change routing with no redeploy
- Response headers tell you which model actually answered. Log it; it's README material
- Set timeouts and a per-key spend cap

Use for: ranking rationale, call summarization, email drafting. **Not** for the realtime voice leg.

→ [API quickstart](https://openrouter.ai/docs/quickstart) · [Model catalog](https://openrouter.ai/models)

### Exa
Search built for agents — neural search, dense highlights, citations.

Two honest uses here:
1. **Card enrichment** — transit times, building reputation, recent neighbourhood news. Things a listing omits
2. **Finding the listing agent's contact details** when the listing doesn't carry one

Fetch it *while the caller is still talking* so cards fill in as they read. Never block speech on it.

Exa credits ride on all three podium places, so judges demonstrably value it.

→ [Exa docs](https://docs.exa.ai/)

### CopilotKit · named award
The Agentic Application Platform — AG-UI protocol, generative UI, in-app actions, plus a **Channels SDK** that puts one agent into Slack and Teams.

**Our angle:** the live page. Cards assembled from streaming agent state is precisely what AG-UI exists for, which makes this a real shot at the award rather than a bolt-on.

**Judgement call, stated plainly:** if nobody on the team is already fluent in CopilotKit, build the page with plain React and a 1s poll, and forget the award. Don't let award-chasing sink the build.

→ [CopilotKit quickstart](https://docs.copilotkit.ai/) · [Channels setup](https://docs.copilotkit.ai/slack/connect)

### Twilio · not a sponsor, but required
Phone number (Voice **and** SMS), outbound dialling, and the SMS that carries the live link. The handbook explicitly allows any stack.

---

## Optional — only if ahead

### Trigger.dev
Open-source durable background jobs in TypeScript. `task()`, scheduled tasks, automatic retries, queues, idempotency keys, `waitForToken` for human-approval gates, and a Realtime API with React hooks.

**Where it fits:** fanning out the three concurrent calls with per-call timeouts, returning partial results when one doesn't answer, and owning the retry-or-escalate-to-email decision. Its run trace is good README material.

**But:** `asyncio.gather` does the same job in ten lines and we're already in Python. Take Trigger.dev only if you want the sponsor story and have the time.

→ [Trigger.dev docs](https://trigger.dev/docs)

### Ambiguous AI · named award, DGX Spark
A workspace of 17 apps — Docs, Sheets, Mail, Chat, CRM, Calendar — where each AI coworker has its own identity and endpoint. Agents connect over MCP or CLI. Free for teams up to five.

**Our angle:** write the verified shortlist as a Doc and the booked viewing as a Calendar entry. ~20 minutes after 13:30.

**Be honest about the odds:** winning this category needs an agent that genuinely lives across several apps. One tool call once reads as "environment as wrapper," which the rubric scores a 2. Treat it as a cheap lottery ticket, not a strategy.

→ ambiguous.ai/agents (endpoint, CLI command and auth are in the signed-in dashboard)

### Auth0
Identity for agents — Token Vault for scoped OAuth tokens with auto-refresh, and CIBA async authorization for push-approval before a sensitive action.

**Skipping it.** Our page *is* the approval surface — tapping a card is better controllability than a push notification and costs nothing extra.

### Mozilla.ai
`any-agent` (one interface across agent frameworks with normalized OpenTelemetry tracing), `any-llm`, `any-guardrail`, `mcpd`.

**Skipping it.** Clean traces are nice; they don't move any of the four criteria far enough to justify the wiring today.

### Google Cloud Run
`gcloud run deploy` from source, generous free tier.

**Skipping it for the demo.** We need a long-running process holding live sessions; scale-to-zero kills them. Laptop behind ngrok, page on Vercel — the same shape SITE COBRA used at 3rd place.

---

## Mapping, at a glance

| Section of the build | Tool |
|---|---|
| Inbound + outbound voice | OpenAI Realtime + Twilio Media Streams |
| Preference extraction | OpenAI structured outputs |
| Call-outcome extraction | OpenAI structured outputs |
| Ranking rationale, email drafting | OpenRouter (preset with fallback) |
| Card enrichment | Exa |
| The live page | Next.js + polling · CopilotKit AG-UI if fluent |
| Parallel call orchestration | `asyncio.gather` · Trigger.dev if ahead |
| SMS | Twilio |
| Shortlist as a Doc | Ambiguous AI, if ahead |
| Tunnel / hosting | ngrok + Vercel |

---

## Required at submission

Five items, all five mandatory:

1. Project title
2. Written description
3. **Public** GitHub repo
4. Two-minute demo video
5. Social post tagging **OpenAI, Georgian, CopilotKit, OpenRouter, AI Tinkerers, Human Feedback Foundation**

Assign the social post to a person, not to the team. It takes ninety seconds and it is the one people forget.
