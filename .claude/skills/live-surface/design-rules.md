# Design rules for `web/`

Non-negotiable. A reviewer called the first version "completely vibe coded" and
they were right — it hit six documented AI-design tells at once. Any change to
the UI is measured against this list before it ships.

## Banned outright

| Don't | Why |
|---|---|
| Cards with `rounded-*` + `ring`/`shadow` | The shadcn default look. The single loudest tell |
| Pill badges (`rounded-full` + tint bg + coloured text) | Status is a **word**, set in its colour |
| All-caps labels and eyebrows | Sentence case. Weight and size carry hierarchy |
| Coloured left/top border stripes on blocks | Described as "almost as reliable a sign of AI design as em-dashes are for AI text" |
| `backdrop-blur` headers / glassmorphism | Header is solid with a hairline under it |
| Gradients, coloured glows, coloured shadows | We have no shadows at all |
| Inter, Geist, Space Grotesk, Instrument Serif | Archivo + JetBrains Mono. Pairing is deliberate |
| Purple / lavender / blue-500 accents | Ink, paper, and three status colours. Nothing else |
| Identical repeated blocks with an icon on top | Rank 1 is visibly larger. Hierarchy is real, not decorative |
| Emoji as UI | Never |
| Uniform `p-4` / `gap-6` everywhere | Spacing varies with importance |

## What this design is instead

**A ledger, not a dashboard.** The page is a verification record — what was
listed, what turned out to be true, who said so — so it's built like a printed
table: hairline rules, flush-left type, figures aligned to a right column.

- **Light only.** A committed single ground, so status colours work as body text
- **No radius anywhere.** Square photos, square buttons, square everything
- **Rules, not boxes.** `border-b border-hair` between rows
- **The correction is the hero.** Real rent large and in `gone` red, listed rent
  struck beneath it in mono. That treatment is the product
- **Provenance in mono under every verified row** — `Dana · 1:41pm`
- **Tabular numerals** on every figure, or the ledger twitches between polls
- **Motion is functional only:** `layoutId` reorder, and a hairline sweeping
  under a row that's being called. No fade-ins on load

## Before you ship a UI change

1. Screenshot it at 375px **and** desktop
2. Read the banned list above, top to bottom, against your diff
3. Ask: *would this look identical if it were for a to-do app?* If yes, it's
   generic — the design must be specific to a verification record
