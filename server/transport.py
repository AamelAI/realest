"""The CallTransport seam.

TODO.md's `1.6` asks for a transport interface so D2's call -> outcome -> re-rank
logic never has to wait on a real phone: `RealTransport` wraps the existing,
already-working Twilio path in `calls.place_call()` unchanged; `StubTransport`
fabricates a deterministic transcript so the whole pipeline (extraction,
state write, re-rank) is testable with no Twilio/OpenAI credentials at all.

Neither transport touches bridge.py's audio/barge-in logic. A real call's
outcome still arrives the way it already does - the model calling
`record_outcome` live, or bridge.py's hangup safety net - `RealTransport`
here only fires the call. `StubTransport` is the one that manufactures a
transcript and pushes it through the same completion path.
"""
from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod


class CallTransport(ABC):
    @abstractmethod
    async def place_call(self, session_id: str, listing_id: str, extra_questions: list[str]) -> None:
        """Fire the call. Must not return the outcome - it must eventually be
        delivered via calls.complete_call(), on whatever timeline this
        transport actually has (a real call: minutes, out of band, via the
        bridge; the stub: a short deterministic delay, right here)."""


class RealTransport(CallTransport):
    """Thin wrapper - no new behaviour. `calls.place_call()` is the existing,
    already-working Twilio implementation; this only gives it the interface
    shape `fan_out()` now expects."""

    async def place_call(self, session_id: str, listing_id: str, extra_questions: list[str]) -> None:
        import calls
        await calls.place_call(session_id, listing_id, extra_questions)
        # The outcome is NOT produced here. It arrives later, out of band,
        # from the live call via bridge.py (record_outcome tool, or the
        # hangup safety net) - exactly as it does today without this seam.


# Canned per-listing transcripts for demo/dev. Keyed by address fragment so it
# still hits without knowing exact seeded ids. Falls through to a generic one.
_CANNED: dict[str, str] = {
    "wellington": (
        "Agent: Hi, this is Dana.\n"
        "Us: Hi Dana, I'm an AI assistant calling on behalf of a client about "
        "700 Wellington St W. Is it still available?\n"
        "Agent: Yes, still available.\n"
        "Us: What does parking actually cost on top of the listed rent?\n"
        "Agent: Parking is an extra $180 a month, and there's a $40 locker fee too.\n"
        "Us: Got it. What's the pet policy?\n"
        "Agent: No pets, sorry.\n"
        "Us: Understood, thanks for your time."
    ),
    "strachan": (
        "Agent: Hello?\n"
        "Us: Hi, I'm an AI assistant calling about 155 Strachan Ave. Is it still available?\n"
        "Agent: Oh, that one's actually already leased - went Tuesday.\n"
        "Us: Ah, thanks for letting me know."
    ),
    "lynn williams": (
        "Agent: Hi, this is Priya.\n"
        "Us: Hi Priya, calling on behalf of a client about 80 Lynn Williams St. "
        "Still available?\n"
        "Agent: Yes it is.\n"
        "Us: What does parking cost, and is there a locker included?\n"
        "Agent: Parking's included, and yes, locker's included too.\n"
        "Us: Great, and pets?\n"
        "Agent: Cats only, no dogs.\n"
        "Us: Could we book a viewing?\n"
        "Agent: Saturday at 2pm works.\n"
        "Us: Perfect, thank you."
    ),
}
_DEFAULT_TRANSCRIPT = (
    "Agent: Hello?\n"
    "Us: Hi, I'm an AI assistant calling on behalf of a client about {address}. "
    "Is it still available?\n"
    "Agent: Yes, still available, nothing unusual to report.\n"
    "Us: Thanks for your time."
)

STUB_DELAY_S = float(os.getenv("STUB_CALL_DELAY", "2"))


class StubTransport(CallTransport):
    """Deterministic fake call for development and demo without a phone.

    Sleeps a short, configurable delay (default 2s - long enough that three
    cards visibly flip to CALLING together, short enough to not stall a demo),
    then runs a canned transcript through the SAME extract_outcome() a real
    call uses, and delivers it through the same completion path.
    """

    async def place_call(self, session_id: str, listing_id: str, extra_questions: list[str]) -> None:
        import calls
        import listings as L

        await asyncio.sleep(STUB_DELAY_S)

        lst = L.by_id(listing_id)
        address = lst.address if lst else listing_id
        transcript = _DEFAULT_TRANSCRIPT.format(address=address)
        for key, canned in _CANNED.items():
            if lst and key in lst.address.lower():
                transcript = canned
                break

        outcome = await calls.extract_outcome(transcript, extra_questions)
        await calls.complete_call(session_id, listing_id, outcome)


_transport: CallTransport | None = None


def get_transport() -> CallTransport:
    """Auto: real if Twilio is actually configured, stub otherwise - so D2's
    loop never blocks on D4/Twilio setup. Override with CALL_TRANSPORT=stub|real."""
    global _transport
    if _transport is not None:
        return _transport

    mode = os.getenv("CALL_TRANSPORT", "").strip().lower()
    if mode == "stub":
        _transport = StubTransport()
    elif mode == "real":
        _transport = RealTransport()
    else:
        have_twilio = bool(os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"))
        _transport = RealTransport() if have_twilio else StubTransport()
    return _transport


def set_transport(t: CallTransport | None) -> None:
    """Test hook - force a specific transport (or None to re-run auto-detect)."""
    global _transport
    _transport = t
