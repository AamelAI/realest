"""D2 end-to-end smoke test: start_calls -> transport -> outcome -> state -> re-rank.

Exercises the real HTTP handlers in server/main.py against the stub transport
(TRANSPORT=stub, the default), so the whole D2 loop is verifiable with no
Twilio/OpenAI credentials and no phone involved.

    uv run pytest tests/test_d2_transport.py -q
    python3 tests/test_d2_transport.py           # also runs standalone
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

import main  # noqa: E402
import state as store  # noqa: E402
import transport  # noqa: E402
from schemas import CallStatus  # noqa: E402


def _check(label: str, cond: bool, failures: list[str], detail: str = "") -> None:
    print(("  \033[32mPASS\033[0m " if cond else "  \033[31mFAIL\033[0m ") + label + (f"  {detail}" if detail else ""))
    if not cond:
        failures.append(label)


async def _run() -> list[str]:
    failures: list[str] = []
    transport.DELAY_RANGE = (0, 0)  # no need to wait in a test

    sid = "test-d2-session"

    print("\nstep 1 - preferences set a shortlist")
    await main.agent_preferences({
        "session_id": sid, "beds": 2, "areas": ["King West", "Liberty Village"],
        "max_rent": 3400, "parking": True, "pets": "dog",
        "priority_order": ["parking", "price"],
    })
    s = store.get(sid)
    _check("shortlist non-empty", len(s.listings) > 0, failures, f"{[l.listing_id for l in s.listings]}")
    _check("all pending, none calling/verified yet",
           all(l.status is CallStatus.PENDING for l in s.listings), failures)

    ids = [l.listing_id for l in s.listings[:2]]

    print(f"\nstep 2 - start_calls({ids}) fans out through the stub transport")
    r2 = await main.agent_start_calls({"session_id": sid, "listing_ids": ids, "extra_questions": ["is there a locker?"]})
    _check("handler returned before hanging", isinstance(r2.get("speak"), str), failures)

    s2 = store.get(sid)
    by_id = {l.listing_id: l for l in s2.listings}
    for lid in ids:
        got = by_id[lid].status
        _check(f"{lid} resolved out of CALLING", got is not CallStatus.CALLING, failures, f"status={got}")
        _check(f"{lid} has an outcome", by_id[lid].outcome is not None, failures)
        _check(f"{lid} has provenance (raw_transcript non-empty)",
               bool(by_id[lid].outcome and by_id[lid].outcome.raw_transcript), failures)
        _check(f"{lid} outcome.source is always set (2.1's own acceptance criterion)",
               bool(by_id[lid].outcome and by_id[lid].outcome.source), failures)

    print("\nstep 3 - re-rank actually ran (agent_says reflects the calls)")
    _check("agent_says was updated", bool(s2.agent_says), failures, s2.agent_says)

    print("\nstep 4 - no-answer path: an id with no listing behind it times out gracefully")
    before = len(store.get(sid).listings)
    await main.agent_start_calls({"session_id": sid, "listing_ids": ["NOT-A-REAL-ID"], "extra_questions": []})
    _check("fake id didn't crash the handler and state is intact", len(store.get(sid).listings) == before, failures)

    print("\nstep 5 - outside business hours: declines to call, drafts email instead")
    import calls
    real_check = calls.within_business_hours
    calls.within_business_hours = lambda *a, **k: False  # deterministic, no clock dependency
    try:
        r5 = await main.agent_start_calls({"session_id": sid, "listing_ids": ids, "extra_questions": []})
        _check("declines to call and drafts email instead",
               r5.get("called") == 0 and r5.get("emailed") == len(ids), failures)
        s5 = store.get(sid)
        _check("email_draft present on the cards",
               all(l.email_draft for l in s5.listings if l.listing_id in ids), failures)
    finally:
        calls.within_business_hours = real_check

    return failures


def test_d2_transport_end_to_end() -> None:
    failures = asyncio.run(_run())
    assert not failures, f"{len(failures)} check(s) failed: {failures}"


if __name__ == "__main__":
    test_d2_transport_end_to_end()
    print("\n\033[32mall D2 transport checks pass\033[0m\n")
