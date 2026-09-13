"""Renter conversation bind + live contextual inject. No real phones."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

import calls  # noqa: E402
import main  # noqa: E402
import state as store  # noqa: E402
from schemas import CallStatus  # noqa: E402


class _FakeInitRequest:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def json(self) -> dict:
        return self._payload


def setup_function() -> None:
    calls._renter_conversation.clear()


def test_bind_only_accepts_conv_ids() -> None:
    assert calls.bind_renter_conversation("s1", "conv_abc123xyz") == "conv_abc123xyz"
    assert calls.renter_conversation("s1") == "conv_abc123xyz"
    assert calls.bind_renter_conversation("s1", "not-a-conv") == ""
    assert calls.bind_renter_conversation("s1", "") == ""
    assert calls.renter_conversation("s1") == "conv_abc123xyz"


def test_init_binds_conversation_id() -> None:
    async def run() -> None:
        init = await main.agent_init(_FakeInitRequest({
            "caller_id": "+14165550101",
            "conversation_id": "conv_renter_init_1",
        }))
        sid = init["dynamic_variables"]["session_id"]
        assert calls.renter_conversation(sid) == "conv_renter_init_1"

    asyncio.run(run())


def test_later_tool_binds_if_init_missed() -> None:
    async def run() -> None:
        sid = "inject-late-bind"
        await main.agent_preferences({
            "session_id": sid,
            "beds": 2,
            "max_rent": 3000,
            "conversation_id": "conv_from_prefs",
        })
        assert calls.renter_conversation(sid) == "conv_from_prefs"

    asyncio.run(run())


def test_notify_skips_when_unbound() -> None:
    async def run() -> None:
        assert await calls.notify_renter("no-such-session", "L001") is False

    asyncio.run(run())


def test_inject_context_skips_without_key() -> None:
    from voice.elevenlabs import ElevenLabsProvider

    async def run() -> None:
        p = ElevenLabsProvider(env={})
        assert await p.inject_context("conv_abc", "hello") is False
        p2 = ElevenLabsProvider(env={"ELEVENLABS_API_KEY": "sk-test"})
        assert await p2.inject_context("", "hello") is False
        assert await p2.inject_context("conv_abc", "") is False

    asyncio.run(run())


def test_outcome_still_writes_if_inject_fails() -> None:
    async def run() -> None:
        sid = "inject-fail-ok"
        await main.agent_preferences({
            "session_id": sid, "beds": 2, "max_rent": 4000,
            "conversation_id": "conv_will_fail_inject",
        })
        s = store.get(sid)
        assert s and s.listings
        lid = s.listings[0].listing_id

        with patch.object(calls, "notify_renter", new_callable=AsyncMock,
                          side_effect=RuntimeError("monitor down")):
            # create_task would see the raise; call outcome then notify ourselves
            r = await main.agent_outcome({
                "session_id": sid, "listing_id": lid, "available": True,
                "source": "agent, 2:00pm",
            })
        assert r["session_id"] == sid
        s2 = store.get(sid)
        card = next(st for st in s2.listings if st.listing_id == lid)
        assert card.outcome is not None
        assert card.status is not CallStatus.CALLING

        with patch("voice.ElevenLabsProvider.inject_context",
                   new_callable=AsyncMock, side_effect=RuntimeError("ws down")):
            ok = await calls.notify_renter(sid, lid)
        assert ok is False

    asyncio.run(run())


def test_notify_calls_inject_when_bound() -> None:
    async def run() -> None:
        sid = "inject-ok"
        calls.bind_renter_conversation(sid, "conv_live_renter")
        await main.agent_preferences({
            "session_id": sid, "beds": 2, "max_rent": 4000,
        })
        lid = store.get(sid).listings[0].listing_id
        await main.agent_outcome({
            "session_id": sid, "listing_id": lid, "available": True,
            "viewing_slot": "Saturday at one",
            "source": "agent, 2:00pm",
        })
        with patch("voice.is_elevenlabs", return_value=True), \
             patch("voice.get_provider") as gp:
            gp.return_value.inject_context = AsyncMock(return_value=True)
            ok = await calls.notify_renter(sid, lid)
        assert ok is True
        gp.return_value.inject_context.assert_awaited()
        sent = gp.return_value.inject_context.await_args.args[1]
        assert "Saturday at one" in sent
        assert "start_calls" in sent

    asyncio.run(run())
