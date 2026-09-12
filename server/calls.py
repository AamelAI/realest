"""Outbound calls and CallOutcome extraction.

Read .claude/skills/voice-calls/ first.
DO NOT build an audio pipeline. The managed provider owns audio entirely.
"""
from __future__ import annotations

from schemas import CallOutcome, Listing

BUSINESS_HOURS = (9, 19)  # local; outside this the agent declines and offers email


def within_business_hours() -> bool:
    """TODO(hackathon): local-time check. Outside hours the agent DECLINES to
    dial and says why - that is judgment about human norms, not a retry, and
    it belongs on camera."""
    raise NotImplementedError


async def place_call(session_id: str, listing: Listing, extra_questions: list[str]) -> str:
    """One POST. Returns conversation_id.

    Pass session_id and listing_id as dynamic variables - they come back on the
    outcome webhook and are how you know which card to update.

    TODO(hackathon): implement.
    """
    raise NotImplementedError


async def fan_out(session_id: str, listings: list[Listing], extra_questions: list[str]) -> list:
    """Three at once.

    - Flip each card to CALLING BEFORE awaiting, so all three light up together.
      That simultaneity is the shot.
    - asyncio.gather(..., return_exceptions=True) - one failure must not kill the rest.
    - asyncio.wait_for(..., timeout=90) per call. Never leave a card spinning.
    - Timeout or exception -> NO_ANSWER -> draft the email.

    TODO(hackathon): implement.
    """
    raise NotImplementedError


async def extract_outcome(transcript: str, extra_questions: list[str]) -> CallOutcome:
    """Transcript -> CallOutcome via OpenAI structured outputs.

    Never invent a field the human didn't say. Always populate `source`
    ("Mark, 1:42pm") - provenance is what turns the page into evidence.

    TODO(hackathon): implement.
    """
    raise NotImplementedError


async def draft_email(listing: Listing, extra_questions: list[str]) -> str:
    """Nobody answered, or it's the wrong hour. Draft, show on the card, one tap
    to send. Do not build SMTP plumbing.

    TODO(hackathon): implement.
    """
    raise NotImplementedError
