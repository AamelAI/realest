"""Admin monitor: webhook ring, live in-flight start_calls, tool timeline parse."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

import admin as monitor  # noqa: E402
import calls  # noqa: E402


FIXTURE = {
    "transcript": [
        {
            "role": "agent",
            "message": "Calling now.",
            "tool_calls": [
                {
                    "tool_name": "start_calls",
                    "tool_call_id": "tc1",
                    "params_as_json": '{"listing_ids":["L001"]}',
                }
            ],
        },
        {
            "role": "agent",
            "tool_results": [
                {
                    "tool_name": "start_calls",
                    "tool_call_id": "tc1",
                    "result_value": '{"called":1}',
                    "is_error": False,
                }
            ],
        },
    ]
}


def setup_function() -> None:
    monitor.reset()
    calls._renter_conversation.clear()
    calls._conversations.clear()


def test_record_appears_on_live() -> None:
    calls.bind_renter_conversation("sess-live", "conv_admin_1")
    monitor.record("sess-live", "renter", "init", "ok", conversation_id="conv_admin_1")

    async def run() -> None:
        data = await monitor.live_payload()
        assert data["calls"]
        row = next(c for c in data["calls"] if c["session_id"] == "sess-live")
        assert row["conversation_id"] == "conv_admin_1"
        assert "init" in row["tools"]

    asyncio.run(run())


def test_live_marks_start_calls_in_flight() -> None:
    calls.bind_renter_conversation("sess-wait", "conv_admin_wait")
    monitor.record("sess-wait", "renter", "preferences", "ok")
    monitor.record("sess-wait", "renter", "start_calls", "started", summary="L001")

    async def run() -> None:
        data = await monitor.live_payload()
        row = next(c for c in data["calls"] if c["session_id"] == "sess-wait")
        assert row["current_tool"] == "start_calls"
        assert row["status"] == "in_flight"

    asyncio.run(run())


def test_tools_of_pairs_call_and_result() -> None:
    tools = calls.tools_of(FIXTURE)
    assert len(tools) == 1
    name, params, res = tools[0]
    assert name == "start_calls"
    assert "L001" in params
    assert res.get("result_value") == '{"called":1}'
    turns = calls.transcript_turns(FIXTURE)
    assert turns[0]["text"] == "Calling now."
