"""Load seeded listings and rank them.

Read .claude/skills/ranking/ first. The reshuffle is the submission.
"""
from __future__ import annotations

from schemas import CallOutcome, Listing, ListingState, Preferences


def load(path: str = "data/listings.json") -> list[Listing]:
    """TODO(hackathon): read the seeded JSON into Listing models."""
    raise NotImplementedError


def rank(
    listings: list[Listing],
    prefs: Preferences,
    outcomes: dict[str, CallOutcome],
) -> list[ListingState]:
    """Pure function. No I/O, no awaits - this runs while someone is mid-sentence.

    Rules, in order of force:
      1. DEAD sinks to the bottom, always.
      2. real_rent (listed + mandatory add-ons) replaces listed rent once known.
         Over max_rent -> demote hard.
      3. VERIFIED outranks PENDING at equal fit.
      4. Then weighted preference fit, using the MOST RECENTLY stated priorities.
      5. Hard conflicts (dog vs cats-only) annotate, they never remove.

    Ties must be stable - use previous rank as tiebreaker or the cards jitter
    between polls, which looks broken on video.

    TODO(hackathon): implement.
    """
    raise NotImplementedError


def explain(states: list[ListingState], outcomes: dict[str, CallOutcome]) -> str:
    """One breath the agent says out loud: what changed -> why -> what's on top.

    Cite the call, not the data. Compute the ORDER in code; a model may only
    write the prose.

    TODO(hackathon): implement.
    """
    raise NotImplementedError
