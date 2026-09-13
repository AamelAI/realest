# Design rules for `web/`

Non-negotiable. The first version of this page was called "completely vibe coded",
and an audit of the second found the accent was Tailwind's `indigo-800` — the most
recognised tell of AI-built UI. Any change to the UI is measured against this list.

## The idea

**A calm record of phone calls.** Realest's whole claim is that a human told us
this. So the page reads like evidence, not a dashboard: warm-neutral ink on white,
colour that only ever means status, money as the largest thing on screen, and a
name on every fact a person gave us.

## The system

| | Rule |
|---|---|
| **Colour** | Ink `#1a1815`, ink-2 `#55524e`, ink-3 `#6c6864` on white and a `#fbfaf9` ground. Every text colour ≥ 4.5:1. **Ink is the primary action and the focus ring.** |
| **Status** | Three hues only — confirmed `#216a49`, live `#935a11`, gone `#af2b25` — as a dot plus a word, never colour alone. "No answer" is ink: a normal outcome, not a warning |
| **Type** | Instrument Sans, variable. Scale 32 · 28 · 20 · 17 · 15 · 13, whole pixels only. Weights 400 / 540 / 580, never 700. **Nothing under 13px** |
| **Money** | In the sans with `tabular-nums`, largest on the card. A correction shows the real figure in ink, "Listed ~~$x~~" with the word, and the signed delta in the status colour |
| **Provenance** | The call's `source` is rendered verbatim — never parsed, never given a time it didn't come with. What a human said is ink; what the listing claims is grey under "Listed" |
| **Surfaces** | White cards, 16px radius, a hairline. The lead card carries the page's only shadow. No dark panels on the light page |
| **Mono** | IBM Plex Mono for a running clock and nothing else |
| **Motion** | Only for something that changed. Enter short and near-final (≤240ms). The reorder travels by transform and crossing cards stack by direction. One heartbeat on screen at a time. Reduced motion stops travel and loops, keeps fades |
| **Copy** | Sentence case, digits, no exclamation marks, no hype. Say what's missing and when it appears |

## Banned outright

| Don't | Why |
|---|---|
| Tailwind default colours as the brand — indigo, violet, amber | Readers recognise default palettes even when they can't name them |
| Tinted pill badges for status | Reads as an admin dashboard. The attributed fact is the badge |
| All-caps labels and eyebrows | Sentence case. Weight and size carry hierarchy |
| Coloured left/top stripes or coloured card borders | The status word already says it |
| Glass or blur on content | Glass belongs only to a layer floating above content, never on the cards themselves |
| Gradients, glows, coloured shadows | Depth is a hairline and, at most, one barely-there shadow |
| Inter, Geist, Space Grotesk, Instrument Serif | The faces every generated page uses |
| Invented progress — "Dialing…", "Ringing…", ETAs, a pulse over a dead connection | The page shows only states the server reports. "Starting call…" states what the renter did |
| Scores, match percentages, confidence bars | Invented precision on a product whose claim is that nothing is invented |
| A relative time the page can't back up ("just now") | It goes stale on screen |
| Emoji as UI | Never |

## Before you ship a UI change

1. Screenshot at 375px **and** desktop, with every card status on screen at once
2. Nothing under 13px, nothing below 4.5:1, no horizontal overflow
3. During a live re-rank the DOM order of cards is unchanged while their positions move
4. Read the banned list against your diff
5. Ask: *would this look identical if it were a to-do app?* If yes, it is generic
