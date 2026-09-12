"""How a call to a listing agent actually gets made.

Two implementations behind one interface, chosen by TRANSPORT in .env:

    TRANSPORT=stub    a scripted listing agent answers. No telephony.
    TRANSPORT=voice   Twilio dials for real (server/calls.place_call).

The stub is not a mock of the product - it is a mock of the *phone network*.
The transcript it returns goes through the real extract_outcome(), so
structured-output extraction, the CallOutcome schema and the re-rank are all
genuinely exercised. Only the dial tone is fake.

That is what lets three lanes build and rehearse the whole demo by typing while
voice lands in parallel. When D4 is ready, flip one env var.

Scripts live in SCRIPTS below and mirror docs/DEMO.md. A listing with no script
gets a plausible generic answer, so the stub never blocks an unplanned session.
"""
from __future__ import annotations

import asyncio
import os
import random

import listings as L

# Roughly how long a real 45-second call takes to come back. Staggered so the
# three cards don't all resolve on the same tick - that stagger is the thing
# that reads as "these are separate phone calls" on camera.
DELAY_RANGE = (6.0, 11.0)

# id -> what the listing agent says. Straight from docs/DEMO.md - these MUST
# stay in sync with that file's four canonical demo listings (see
# tests/test_demo_scripts.py, which fails loudly the moment they drift again).
# None means nobody picks up.
SCRIPTS: dict[str, str | None] = {
    # DEAD - opens at #1, "leased Tuesday", ends at #4
    "L092": (
        "Agent: Hi, this is the leasing office for 155 Yorkville Avenue.\n"
        "AI: Hi, I'm an AI assistant calling on behalf of a client about 155 "
        "Yorkville Avenue. Is that one still available?\n"
        "Agent: Oh - no, sorry, that one's gone. We leased it Tuesday. I keep meaning "
        "to pull the listing down.\n"
        "AI: Understood, thanks very much for your time.\n"
        "Agent: No problem."
    ),
    # PRICE WRONG - parking is a $180 add-on, $3,290 -> $3,470, over the $3,400 cap
    "L095": (
        "Agent: 322 Dupont, this is Mark.\n"
        "AI: Hi, I'm an AI assistant calling for a client about the unit at "
        "322 Dupont Street. Is it still available, and is parking included in the rent?\n"
        "Agent: It's available, yes. Parking's separate though - that's a hundred and "
        "eighty a month on top.\n"
        "AI: Good to know. Any locker with it?\n"
        "Agent: Lockers are all spoken for in that building right now.\n"
        "AI: Thanks Mark, that's really helpful."
    ),
    # BOOKED - available, Saturday 2pm, but cats only and the caller has a dog
    "L086": (
        "Agent: 155 Yorkville Avenue, Priya speaking.\n"
        "AI: Hi, I'm an AI assistant calling for a client about the unit at "
        "155 Yorkville Avenue. Still available?\n"
        "Agent: It is, yes.\n"
        "AI: Is parking extra, and is there a locker?\n"
        "Agent: Parking's included, and there's a locker with that unit too.\n"
        "AI: And the pet policy?\n"
        "Agent: Cats only in this building, I'm afraid. No dogs.\n"
        "AI: Noted. Could my client view it Saturday afternoon?\n"
        "Agent: Saturday at two works.\n"
        "AI: Perfect, let's hold two o'clock Saturday. Thank you."
    ),
    # NO ANSWER - drafts an email instead
    "L100": None,
}

GENERIC = (
    "Agent: Hello?\n"
    "AI: Hi, I'm an AI assistant calling for a client about the unit at {address}. "
    "Is it still available, and is parking included?\n"
    "Agent: It's still up, yes. Parking's included in the rent for that one.\n"
    "AI: And pets?\n"
    "Agent: Pets are fine.\n"
    "AI: Great - could they view it Saturday afternoon?\n"
    "Agent: Saturday at one, sure.\n"
    "AI: Thank you."
)


def mode() -> str:
    """`stub` unless someone has explicitly switched to real telephony."""
    return os.getenv("TRANSPORT", "stub").strip().lower()


def is_stub() -> bool:
    return mode() != "voice"


async def stub_call(listing_id: str, extra_questions: list[str]) -> str | None:
    """A scripted listing agent answers. Returns a transcript, or None for no answer.

    The delay is deliberate: cards should sit in CALLING long enough that the
    reshuffle is a visible event rather than an instant repaint.
    """
    await asyncio.sleep(random.uniform(*DELAY_RANGE))

    if listing_id in SCRIPTS:
        script = SCRIPTS[listing_id]
        if script is None:
            return None              # nobody picks up -> NO_ANSWER -> email
        transcript = script
    else:
        lst = L.by_id(listing_id)
        transcript = GENERIC.format(address=lst.address if lst else "the unit")

    # If the caller asked us something extra, the agent answers that too - the
    # whole point is that we bring back what the listing never said.
    if extra_questions:
        asks = "; ".join(extra_questions)
        transcript += (
            f"\nAI: One more thing my client asked - {asks}?\n"
            "Agent: Yes, that's included."
        )
    return transcript
