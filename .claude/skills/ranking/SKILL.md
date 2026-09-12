---
name: ranking
description: Ranking listings against caller preferences and merging call outcomes back into the shortlist. Use when working on server/listings.py, the re-rank after a preference change, or deciding how a call result reorders the cards.
---

# Ranking

The reshuffle is the submission. Everything else is setup.

## Why this function matters more than it looks

A judge watching two minutes of video needs to see the top pick die and a fourth-place listing climb to #1 — and needs to understand *why* in one sentence. That sentence comes from here.

The pitch is: **the ranking is not computed from data, it's computed from phone calls placed to humans thirty seconds ago.** Keep that literally true. Every reorder after a call must be traceable to something a person said.

## Signature

Pure function. No I/O, no model calls, no awaits.

```python
def rank(
    listings: list[Listing],
    prefs: Preferences,
    outcomes: dict[str, CallOutcome],
) -> list[ListingState]:
```

Runs on two triggers: a preference change, and a call outcome landing. Nowhere else.

**Keep it synchronous and in-memory.** It runs while someone is mid-sentence on a phone call. A network hop here is dead air, and dead air reads as broken.

## Rules, in order of force

1. **`DEAD` sinks.** Always bottom, regardless of fit. The unit is gone.
2. **Real rent beats listed rent.** `real_rent = listed + mandatory add-ons`. Once known, it replaces the listed figure everywhere. If `real_rent > max_rent`, demote hard — it's over budget and the caller should hear that.
3. **Verified outranks pending** at equal fit. Confirmed beats hypothetical.
4. **Then weighted preference fit**, using the weights the caller stated *most recently*.
5. **Hard conflicts annotate, they don't remove.** Dog vs cats-only stays on the list with a flag. The caller decides, not us.

**Neighbourhoods are fuzzy on purpose.** Exact area match scores **30**, a walkable neighbour **14**, anywhere else **−30** (`NEARBY` in `server/listings.py`). A caller who says "King West" means "or near enough that I'd still go and see it" — strict matching returns an empty shortlist, which is worse than a Liberty Village unit one streetcar stop away. Exact hits always outrank neighbours, and the card shows the real neighbourhood, so nothing is hidden.

Rule 5 is the controllability story. Never silently drop a listing because the agent thinks it's wrong for them.

## Recency-weighted preferences

When a caller says *"actually, being near the streetcar matters more than parking,"* that is a **weight change**, not a filter change. Both listings stay; the order flips.

Simplest thing that works: keep an ordered list of stated priorities, most recent first, and weight by position. Don't build a scoring DSL. You have three hours.

```python
WEIGHTS = {0: 3.0, 1: 2.0, 2: 1.0}  # position in the priority list
```

## Merging a call outcome

```python
def apply_outcome(listing_state, outcome):
    if outcome.available is False:
        listing_state.status = CallStatus.DEAD
    elif outcome.viewing_slot:
        listing_state.status = CallStatus.VERIFIED
    listing_state.outcome = outcome
    # then re-rank the whole list
```

Re-rank the **whole** list after every outcome, not just the affected card. Three calls land at different times; each landing should visibly move the board.

## Explaining the result

The agent has to say the reshuffle out loud in one breath. Generate that line here, alongside the ranking, so the explanation can never drift from the order.

> "Your top pick is gone — leased Tuesday. Wellington is really $3,430 once parking and a locker are in, which puts it over budget. Lynn Williams is available, locker included, Saturday at two."

Pattern: **what changed → why → what's on top now.** Cite the call, not the data. Feed the ranked list plus outcomes to a model through OpenRouter for the prose, but compute the *order* in code — never let a model decide the ranking.

## Provenance on the card

Every fact a call produced carries its `source`: *"parking $180 — Mark, 1:42pm."*

One extra field, and it turns the page from a UI into evidence. Do not skip it.

## Testing

Ranking is the one piece with no external dependencies, so it's the one piece you can actually test. Write three fixtures before you write the function:

1. No outcomes → pure preference fit
2. Top pick returns `available: False` → it sinks, everything shifts up
3. Second pick returns add-ons pushing it over budget → it demotes below a cheaper verified unit

If fixture 2 and 3 both produce the demo's reshuffle, the demo works. That's the fastest confidence you'll get today.

## Gotchas

- **Don't sort in the page.** `listings` arrives ordered; the page renders it as given. Two sort implementations will disagree at the worst moment.
- **Don't re-rank on every poll.** Rank on write, not on read. The page polls 1–2s; ranking there is wasted work and a source of flicker.
- **Ties must be stable.** Unstable sort makes cards jitter between polls, which looks broken on video. Use the previous rank as the tiebreaker.
