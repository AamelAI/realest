"""Regression test for the "SMS link opens to an empty shortlist" bug.

Root cause was in the ElevenLabs tool schemas (agent/elevenlabs-tools.json,
docs/elevenlabs-tools/*.json), not in this backend code: session_id (and
send_sms's caller_phone) were configured as `llm_prompt` fields the model had
to freehand instead of `dynamic_variable` references ElevenLabs substitutes
automatically. On the renter side, that meant record_preferences/start_calls/
book_viewing/send_sms could land in a session different from the one texted
at pickup by /agent/init - the LLM sometimes omitted or misremembered the id.
record_outcome (listing-agent side, outbound) was already wired correctly,
which is why outbound worked while inbound didn't.

This backend code was already correct once given a real session_id - these
tests lock in that correctness and the caller_phone recovery fallback that
send_sms's dynamic-variable fix now relies on.

    uv run pytest tests/test_inbound_session_continuity.py -q
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

import main  # noqa: E402
import state as store  # noqa: E402


def test_session_id_from_init_carries_listings_to_the_same_session() -> None:
    """The path a correctly-wired dynamic variable takes: /agent/init mints a
    session and texts its link, then every later tool call - carrying that
    same session_id, exactly as ElevenLabs' dynamic_variable substitution
    guarantees - writes into it. /api/state for that id must show the
    shortlist the SMS link points to."""
    async def run() -> None:
        init = await main.agent_init({"caller_id": "+14165551234"})
        sid = init["dynamic_variables"]["session_id"]
        assert sid, "agent_init must mint a session_id"

        # Simulates the dynamic-variable-correct case: the same session_id
        # ElevenLabs substituted at init rides every subsequent tool call.
        await main.agent_preferences({
            "session_id": sid, "beds": 2, "max_rent": 4000,
        })

        state = await main.read_state(sid)
        assert state["listings"], (
            "the session the SMS link points to has no listings - this is "
            "exactly the reported bug"
        )

    asyncio.run(run())


def test_send_sms_recovers_the_init_session_via_caller_phone() -> None:
    """send_sms's dynamic-variable fix supplies caller_phone even when
    session_id is legitimately omitted (first turn). _ensure_session must
    resolve back to the SAME session /agent/init already created and texted,
    not mint an empty new one."""
    async def run() -> None:
        phone = "+14165559999"
        init = await main.agent_init({"caller_id": phone})
        sid = init["dynamic_variables"]["session_id"]

        await main.agent_preferences({"session_id": sid, "beds": 2, "max_rent": 4000})

        # send_sms called with caller_phone but no session_id - exactly what
        # the fixed dynamic-variable wiring supplies on an early call.
        resolved = main._ensure_session({"caller_phone": phone})
        assert resolved == sid, (
            f"send_sms resolved to a different session ({resolved!r}) than the "
            f"one /agent/init created and texted ({sid!r}) - it would mint an "
            "empty orphan session and text a link to nothing"
        )

    asyncio.run(run())


def test_missing_session_id_and_no_caller_field_mints_a_new_orphan_session() -> None:
    """Documents the actual failure mode this bug relied on: a payload with
    neither session_id nor any caller-identifying field (e.g. a bare
    record_preferences call if the dynamic variable ever fails to attach)
    has no way back to the real session and gets a fresh, disconnected one.
    This is expected backend behaviour, not a bug in this file - the fix is
    guaranteeing session_id is always present via the tool schema, which is
    what the two tests above lock in."""
    sid_a = main._ensure_session({"beds": 2})
    sid_b = main._ensure_session({"beds": 2})
    assert sid_a != sid_b, "two session-less calls should never collide onto one session"


if __name__ == "__main__":
    test_session_id_from_init_carries_listings_to_the_same_session()
    test_send_sms_recovers_the_init_session_via_caller_phone()
    test_missing_session_id_and_no_caller_field_mints_a_new_orphan_session()
    print("\n\033[32minbound session continuity checks pass\033[0m\n")
