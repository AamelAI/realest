"""Renter availability string is forwarded to the listing outbound."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

import calls  # noqa: E402
import listings as L  # noqa: E402
from bridge import listing_prompt  # noqa: E402
from voice.types import CallHandle  # noqa: E402


def test_listing_prompt_syncs_renter_times() -> None:
    text = listing_prompt("155 Yorkville Ave", 2690, [], "Saturday morning")
    assert "Saturday morning" in text
    assert "landlord" in text.lower()
    assert "confirmation" in text.lower() or "rejection" in text.lower()


def test_listing_prompt_empty_availability_asks_for_a_slot() -> None:
    text = listing_prompt("155 Yorkville Ave", 2690, [], "")
    assert "ask for a viewing slot" in text.lower()


def test_place_call_sends_availability_dynamic_var() -> None:
    lst = L.load()[0]
    captured: list[dict] = []

    async def fake_outbound(**kwargs):
        captured.append(kwargs)
        return CallHandle(conversation_id=None, call_sid="CA-test", provider="elevenlabs")

    async def run() -> None:
        with patch("voice.is_elevenlabs", return_value=True), \
             patch("voice.get_provider") as gp, \
             patch.object(calls, "destination", return_value="+14165550101"):
            gp.return_value.place_outbound = AsyncMock(side_effect=fake_outbound)
            await calls.place_call("sess-avail", lst.listing_id, ["dogs ok?"],
                                   "weeknights after 6")
        assert captured
        dyn = captured[0]["dynamic_variables"]
        assert dyn["availability"] == "weeknights after 6"
        assert dyn["extra_questions"] == "dogs ok?"
        assert dyn["listing_id"] == lst.listing_id

    asyncio.run(run())
