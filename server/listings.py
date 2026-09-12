"""Load seeded listings and rank them.

Read .claude/skills/ranking/ first. The reshuffle is the submission.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from schemas import CallOutcome, CallStatus, Listing, ListingState, Preferences

# Position in the caller's stated priority list -> weight. Most recent first.
WEIGHTS = {0: 3.0, 1: 2.0, 2: 1.0}

_MONEY = re.compile(r"\$?\s*(\d[\d,]*)")


@lru_cache(maxsize=1)
def load(path: str = "data/listings.json") -> list[Listing]:
    """Read the seeded JSON into Listing models."""
    with open(path) as fh:
        rows = json.load(fh)
    return [Listing(**row) for row in rows]


def by_id(listing_id: str) -> Listing | None:
    return next((l for l in load() if l.listing_id == listing_id), None)


def addon_total(outcome: CallOutcome) -> int:
    """Sum the dollar figures a human read out: ['parking $180', 'locker $40'] -> 220."""
    total = 0
    for line in outcome.addons:
        m = _MONEY.search(line)
        if m:
            total += int(m.group(1).replace(",", ""))
    return total


def real_rent(listing: Listing, outcome: CallOutcome | None) -> int:
    """What it ACTUALLY costs. Listed rent until a human corrects it."""
    if outcome is None:
        return listing.rent
    if outcome.real_rent is not None:
        return outcome.real_rent
    return listing.rent + addon_total(outcome)


def _priority_weight(prefs: Preferences, key: str) -> float:
    """How much the caller said this matters, by where they put it in the list."""
    for i, p in enumerate(prefs.priority_order):
        if key in p.lower():
            return WEIGHTS.get(i, 0.5)
    return 1.0


def _transit_minutes(listing: Listing) -> int:
    m = re.search(r"(\d+)\s*min", listing.transit_note)
    return int(m.group(1)) if m else 99


def fit(listing: Listing, prefs: Preferences, outcome: CallOutcome | None) -> float:
    """Weighted preference fit. Higher is better. Pure arithmetic, no I/O.

    Two tiers. Beds and neighbourhood are near-decisive - the caller named them,
    so a wrong-area bargain must never outrank a right-area listing. Everything
    else is weighted by where they put it in their stated priority order.
    """
    score = 0.0
    cost = real_rent(listing, outcome)

    # ── tier 1: what they asked for by name ──────────────────────────────────
    if prefs.beds is not None:
        score += 30.0 if listing.beds == prefs.beds else -18.0 * abs(listing.beds - prefs.beds)
    if prefs.areas:
        hay = f"{listing.neighbourhood} {listing.address}".lower()
        score += 30.0 if any(a.lower() in hay for a in prefs.areas) else -30.0
    if prefs.baths is not None:
        score += 3.0 if listing.baths >= prefs.baths else -4.0

    # ── tier 2: weighted preferences, most recently stated first ─────────────
    if prefs.max_rent:
        w = max(_priority_weight(prefs, "price"), _priority_weight(prefs, "budget"))
        headroom = prefs.max_rent - cost
        if headroom >= 0:
            # Cheaper is better, but capped - fit matters more than pennies.
            score += (2.0 + min(headroom, 700) / 350.0) * w
        else:
            # Over budget. Demote hard, and harder the further over.
            score -= (10.0 + min(-headroom, 800) / 80.0) * w

    if prefs.parking:
        w = _priority_weight(prefs, "parking")
        score += 5.0 * w if listing.parking_included else -2.0 * w

    # Transit only earns points if they said it matters. Saying so is what
    # makes the board visibly reorder mid-sentence.
    tw = max(_priority_weight(prefs, "transit"), _priority_weight(prefs, "streetcar"),
             _priority_weight(prefs, "subway"), _priority_weight(prefs, "walk"))
    if tw > 1.0:
        score += max(0.0, 15 - _transit_minutes(listing)) / 2.0 * tw

    if prefs.pets and prefs.pets.lower() not in ("none", "no", ""):
        stated = (outcome.pets_allowed if outcome and outcome.pets_allowed else listing.pets) or ""
        s = stated.lower()
        if prefs.pets.lower() in s or "yes" in s or "allowed" in s:
            score += 4.0
        elif s and s != "ask":
            # Hard conflict: annotate, never remove. Rule 5.
            score -= 5.0

    return score


def apply_outcome(st: ListingState, outcome: CallOutcome, listing: Listing | None = None) -> None:
    """Merge what a human said into one card's state.

    Resolve real_rent here, once, so the page and the ranker can never disagree
    about what the place actually costs. The struck listed price against the
    real one is the hero of the card - it needs the number, not the arithmetic.
    """
    listing = listing or by_id(st.listing_id)
    if outcome.real_rent is None and listing is not None:
        addons = addon_total(outcome)
        if addons:
            outcome.real_rent = listing.rent + addons
    st.outcome = outcome
    if outcome.available is False:
        st.status = CallStatus.DEAD
    elif st.status is not CallStatus.BOOKED:
        st.status = CallStatus.VERIFIED


def rank(
    listings: list[Listing],
    prefs: Preferences,
    outcomes: dict[str, CallOutcome],
    previous: list[ListingState] | None = None,
) -> list[ListingState]:
    """Pure function. No I/O, no awaits - this runs while someone is mid-sentence.

    Rules, in order of force:
      1. DEAD sinks to the bottom, always.
      2. real_rent (listed + mandatory add-ons) replaces listed rent once known.
         Over max_rent -> demote hard.
      3. VERIFIED outranks PENDING at equal fit.
      4. Then weighted preference fit, using the MOST RECENTLY stated priorities.
      5. Hard conflicts (dog vs cats-only) annotate, they never remove.

    Ties are broken by previous rank, so cards never jitter between polls.
    """
    prev = {s.listing_id: s for s in (previous or [])}

    states: list[ListingState] = []
    for lst in listings:
        old = prev.get(lst.listing_id)
        st = ListingState(
            listing_id=lst.listing_id,
            status=old.status if old else CallStatus.PENDING,
            rank=old.rank if old else 999,
            outcome=old.outcome if old else None,
            email_draft=old.email_draft if old else None,
        )
        oc = outcomes.get(lst.listing_id)
        if oc is not None:
            apply_outcome(st, oc, lst)
        states.append(st)

    lookup = {l.listing_id: l for l in listings}

    def key(st: ListingState):
        lst = lookup[st.listing_id]
        booked = st.status is not CallStatus.BOOKED      # a booked viewing pins to #1
        dead = st.status is CallStatus.DEAD              # 1. a gone unit pins to last
        # 3. VERIFIED outranks PENDING at equal fit. Worth real points on a
        #    30-point scale, or "we phoned and confirmed" loses to a bargain.
        confirmed = 7.0 if st.status is CallStatus.VERIFIED else 0.0
        return (booked, dead, -fit(lst, prefs, st.outcome) - confirmed, st.rank)

    states.sort(key=key)
    for i, st in enumerate(states, start=1):
        st.rank = i
    return states


def explain(
    states: list[ListingState],
    outcomes: dict[str, CallOutcome],
    prefs: Preferences | None = None,
) -> str:
    """One breath the agent says out loud: what changed -> why -> what's on top.

    Cite the call, not the data. The ORDER is computed above; this only narrates
    it, so the explanation can never drift from what the page shows.
    """
    if not states:
        return "Nothing matches yet - tell me a bit more."

    prefs = prefs or Preferences()
    gone: list[str] = []      # what changed, first - it's the headline
    priced: list[str] = []    # then why the money moved
    bits: list[str] = []

    for st in states:
        oc = outcomes.get(st.listing_id)
        if oc is None:
            continue
        lst = by_id(st.listing_id)
        if lst is None:
            continue
        where = lst.address.split(",")[0]
        if st.status is CallStatus.DEAD:
            gone.append(f"{where} is gone - already leased")
        else:
            cost = real_rent(lst, oc)
            if cost != lst.rent:
                over = prefs.max_rent and cost > prefs.max_rent
                extra = ", ".join(oc.addons)
                priced.append(
                    f"{where} is really ${cost:,} once {extra} is in"
                    + (", which puts it over budget" if over else "")
                )

    bits = gone + priced

    top = states[0]
    lst = by_id(top.listing_id)
    if lst is not None:
        where = lst.address.split(",")[0]
        oc = top.outcome
        if oc and oc.viewing_slot:
            bits.append(f"{where} is available, {oc.viewing_slot}")
        else:
            bits.append(f"{where} is on top at ${real_rent(lst, oc):,}")

        # The beat that proves context crossed two separate phone calls.
        if oc and oc.pets_allowed and prefs.pets:
            allowed = oc.pets_allowed.lower()
            if prefs.pets.lower() not in allowed and "ask" not in allowed:
                bits.append(f"One catch: {oc.pets_allowed}, and you mentioned a {prefs.pets}")

    return ". ".join(bits[:4]).strip() + "."
