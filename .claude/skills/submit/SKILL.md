---
name: submit
description: Packaging the hackathon submission — README, two-minute video, written description, social post, repo hygiene. Use at 14:30 feature freeze, or any time someone asks what still needs to ship.
---

# Submission

## The fact that governs everything here

**Nobody judging this will watch your demo.** Toronto's afternoon show-and-tell is explicitly non-judged — every city feeds one global pool. Judges score from four artifacts: title, written description, public GitHub repo, and a two-minute video.

The deliverable is not a working agent. It's **a repo and a video that prove one**. Treat this hour as part of the build.

## Five required items

1. Project title — **Realest**
2. Written description
3. **Public** GitHub repo — *check this, `AamelAI/base` was created private*
4. Two-minute demo video
5. Social post tagging **OpenAI, Georgian, CopilotKit, OpenRouter, AI Tinkerers, Human Feedback Foundation**

Assign item 5 to a person, not to the team. Ninety seconds of work, and it's the one that gets forgotten.

## Description — the first sentence decides everything

Judges read dozens of these. Sentence one determines how carefully they read the rest.

> Every AI voice agent in real estate works for the brokerage. **Realest** works for the renter — you talk, a page in your hand reorders as you talk, and it phones three listing agents at once to find out which listings are actually real.

Then, in order: how it works · the stack with one line per sponsor tool and *which feature* · the number · limitations.

**Never open with "a voice assistant for apartment hunting."** That's the wrapper framing the rubric scores a 2, and voice will be one of the biggest clusters in the pool.

Structure the body under headers that mirror the four criteria. Top-placing entries at past AI Tinkerers events did exactly this, and it makes a judge's scoring job mechanical.

## README — in this order

1. One-line hook (the inversion). Then a ~20-second GIF of the board reshuffling, above everything else
2. **Both call transcripts, in full** — a judge reading the repo cannot hear the product. This is the single highest-value section for a voice project
3. Architecture diagram — one session store, two channels
4. Prior art named — EliseAI, Funnel, Yardi Chat IQ, CloudTalk, Bland — plus the one-line delta: *they all work for the brokerage*
5. The ethics line: identifies itself as an AI in its first sentence, calls only listings you tapped, never cold-dials, won't call outside business hours
6. What's real vs seeded — listings are a dated snapshot with stock photos. Say it plainly
7. Setup in five commands or fewer
8. **Built during the event vs. scaffolded beforehand** — answer it before you're asked
9. Known limitations. Every winner listed theirs

Naming your competitors reads as market awareness. Winners did it on purpose — `/shipit` pitched itself as "Cursor for design"; Recordly called its own output "indistinguishable from a Screen Studio demo."

## Video — 120 seconds

| Time | Shot |
|---|---|
| 0:00 | Cold open on the payoff: *"Your top pick is gone — leased Tuesday."* Card goes red. **No title card** |
| 0:12 | Rewind — preferences spoken, link arrives, cards appear with photos |
| 0:30 | The reorder while he's still speaking. One hand, one shot, phone on speaker |
| 0:45 | *"Anything else you want me to ask?"* → tap three → calls fire |
| 1:05 | Cards resolving live: dead · price wrong · no answer → email drafted |
| 1:25 | The reshuffle and the dog line. Booking. Phone buzzes with the SMS |
| 1:45 | Architecture card, ten seconds. Then the number |
| 1:55 | Closing card: **REAL EST**ATE → **REALEST**. No narration — let a judge find it |

**Shoot it in one take, one hand.** Phone on speakerphone, held in frame, page visible. Hearing the agent and watching the cards reorder in the *same frame* is the entire argument for why this isn't a chatbox.

**Never ship the first take.** Live calls stumble. Three takes minimum, and keep a clean backup recorded at 14:00 in case the last one breaks.

Show a failure. "Thoughtful failure handling" is named in criterion 3's top band, and almost nobody demonstrates it. Let one realtor not answer, on camera, and let the agent switch to email gracefully.

## Repo hygiene — 10 minutes, easy points

```bash
git log --oneline | head -30        # does the history show work done today?
grep -rn "sk-\|AC[0-9a-f]\{32\}" --include="*.py" --include="*.ts" .   # no leaked keys
cat .gitignore | grep -q "^\.env$" && echo "env ignored"
```

- `.env` ignored, `.env.example` committed and complete
- No absolute paths from anyone's laptop
- README setup steps actually run on a clean clone
- **Repo is public**

## The number

Every winner quantified the before/after. GameSight: $50,000 playtest → ~$3. /shipit: 15 min → 5 min.

Ours: time yourselves phoning three listing agents by hand. Realistically twenty minutes of hold music and voicemail versus ninety seconds.

**Measure it honestly.** Don't invent a statistic about stale listings you can't support — a judge who catches one fabricated number discounts everything else on the page.

## Timing

| | |
|---|---|
| 14:00 | Record a clean backup take while the build still works |
| 14:30 | **Freeze.** Whole team on artifacts |
| 14:30 | Dev 1 → README · Dev 3 → video · Dev 2 → description + social post |
| 15:10 | Submit |
| 15:30–16:00 | Official window. Don't cut it fine |

Verify after submitting: repo loads while signed out, video plays for someone who isn't you, all five items present.
