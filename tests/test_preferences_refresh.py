"""Updating preferences rebuilds the shortlist from the full catalogue."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

import listings as L  # noqa: E402
import main  # noqa: E402
import state as store  # noqa: E402


def test_preference_update_replaces_listings() -> None:
    async def run() -> None:
        sid = "prefs-refresh"
        first = await main.agent_preferences({
            "session_id": sid, "beds": 2, "max_rent": 4000,
        })
        ids_a = {row["listing_id"] for row in first["shortlist"]}
        assert ids_a
        for lid in ids_a:
            lst = L.by_id(lid)
            assert lst is not None

        second = await main.agent_preferences({
            "session_id": sid, "beds": 1, "max_rent": 2800,
        })
        ids_b = {row["listing_id"] for row in second["shortlist"]}
        assert ids_b
        assert ids_a != ids_b
        for lid in ids_b:
            lst = L.by_id(lid)
            assert lst is not None
            assert lst.beds == 1
        s = store.get(sid)
        assert s is not None
        assert {st.listing_id for st in s.listings} == ids_b
        assert s.preferences.beds == 1
        assert s.preferences.max_rent == 2800

    asyncio.run(run())


def test_outcome_rerank_keeps_the_same_cards() -> None:
    async def run() -> None:
        sid = "prefs-outcome-keep"
        r = await main.agent_preferences({
            "session_id": sid, "beds": 2, "max_rent": 4000,
        })
        ids = [row["listing_id"] for row in r["shortlist"]]
        assert ids
        lid = ids[0]
        await main.agent_outcome({
            "session_id": sid, "listing_id": lid, "available": True,
            "source": "agent, 2:00pm",
        })
        s = store.get(sid)
        assert s is not None
        assert [st.listing_id for st in s.listings] == ids

    asyncio.run(run())
